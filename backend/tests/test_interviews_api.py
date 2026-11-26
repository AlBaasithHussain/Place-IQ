"""End-to-end tests for mock interview endpoints."""

from types import SimpleNamespace

import pytest

from app.services.interviews import generator
from app.services.interviews.generator import InterviewGenerationError
from app.services.jobs import analyzer
from pdf_utils import make_pdf

RESUME_TEXT = """Alice Example
alice@example.com

Education
B.Tech in Information Technology, NIT Trichy, 2025

Skills
Python, Docker

Projects
Built a Random Forest model for customer churn.

Experience
2 years of software development experience.
"""

JOB_TEXT = """Job Title: Python Developer

Required Skills
Python, SQL, Docker

Preferred Qualifications
Git

Soft skills: Communication

3+ years of experience
Bachelor's degree in Computer Science
"""


@pytest.fixture(autouse=True)
def _force_heuristic(monkeypatch):
    monkeypatch.setattr(analyzer, "settings", SimpleNamespace(llm_enabled=False))
    monkeypatch.setattr(generator, "settings", SimpleNamespace(llm_enabled=False))


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Interview User", "email": email, "password": "Passw0rd1"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _setup_resume_and_job(client, token: str) -> tuple[int, int]:
    upload = client.post(
        "/api/v1/resumes/upload",
        headers=_auth(token),
        files={"file": ("resume.pdf", make_pdf(RESUME_TEXT), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    job = client.post(
        "/api/v1/jobs/analyze", headers=_auth(token), json={"text": JOB_TEXT}
    )
    assert job.status_code == 201, job.text
    return upload.json()["id"], job.json()["id"]


def _start(client, token: str, count: int = 5, resume_id: int = 1, job_id: int = 1):
    return client.post(
        "/api/v1/interviews/start",
        headers=_auth(token),
        json={
            "resume_id": resume_id,
            "job_id": job_id,
            "question_count": count,
        },
    )


def _answer(client, token: str, interview_id: int, question_id: int, text: str = "My answer."):
    return client.post(
        f"/api/v1/interviews/{interview_id}/answer",
        headers=_auth(token),
        json={"question_id": question_id, "answer": text},
    )


def test_start_creates_five_question_interview(client, registered_user):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)

    response = _start(client, token, 5, resume_id, job_id)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["resume_id"] == resume_id
    assert body["job_id"] == job_id
    assert body["job_title"] == "Python Developer"
    assert body["generation_engine"] == "heuristic"
    assert body["status"] == "in_progress"
    assert body["question_count"] == 5
    assert len(body["questions"]) == 5
    assert [item["position"] for item in body["questions"]] == [1, 2, 3, 4, 5]
    assert {item["category"] for item in body["questions"]} == {
        "technical",
        "hr",
        "behavioral",
        "project_based",
        "problem_solving",
    }
    assert all(item["answer"] is None for item in body["questions"])
    assert body["answered_count"] == 0
    assert body["progress_percentage"] == 0
    assert body["current_question_number"] == 1
    assert body["is_complete"] is False


def test_start_creates_ten_question_interview(client, registered_user):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)
    response = _start(client, token, 10, resume_id, job_id)
    assert response.status_code == 201, response.text
    assert len(response.json()["questions"]) == 10


def test_get_and_list_interviews_with_auth(client, registered_user):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)
    created = _start(client, token, 5, resume_id, job_id).json()

    response = client.get(f"/api/v1/interviews/{created['id']}", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["questions"] == created["questions"]

    listing = client.get("/api/v1/interviews", headers=_auth(token))
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["id"] == created["id"]

    assert client.get(f"/api/v1/interviews/{created['id']}").status_code == 401
    assert client.get("/api/v1/interviews").status_code == 401


def test_answer_advances_and_completes_interview(client, registered_user):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)
    interview = _start(client, token, 5, resume_id, job_id).json()

    first = _answer(client, token, interview["id"], interview["questions"][0]["id"])
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["answered_count"] == 1
    assert body["progress_percentage"] == 20
    assert body["current_question_number"] == 2
    assert body["questions"][0]["answer"] == "My answer."
    assert body["questions"][0]["answered_at"] is not None
    assert body["is_complete"] is False

    for question in interview["questions"][1:]:
        response = _answer(client, token, interview["id"], question["id"])
        assert response.status_code == 200, response.text

    final = client.get(f"/api/v1/interviews/{interview['id']}", headers=_auth(token)).json()
    assert final["status"] == "completed"
    assert final["is_complete"] is True
    assert final["answered_count"] == 5
    assert final["progress_percentage"] == 100
    assert final["current_question_number"] is None
    assert final["completed_at"] is not None


def test_completed_interview_rejects_more_answers(client, registered_user):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)
    interview = _start(client, token, 5, resume_id, job_id).json()
    for question in interview["questions"]:
        assert _answer(client, token, interview["id"], question["id"]).status_code == 200

    response = _answer(client, token, interview["id"], interview["questions"][0]["id"])
    assert response.status_code == 400
    assert response.json()["detail"] == "Interview is already completed"


def test_cannot_use_another_users_data(client, registered_user):
    token_a = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token_a)
    interview = _start(client, token_a, 5, resume_id, job_id).json()

    token_b = _register(client, "interview-other@example.com")["access_token"]
    assert _start(client, token_b, 5, resume_id, job_id).status_code == 404
    assert client.get(
        f"/api/v1/interviews/{interview['id']}", headers=_auth(token_b)
    ).status_code == 404
    assert _answer(
        client, token_b, interview["id"], interview["questions"][0]["id"]
    ).status_code == 404


def test_invalid_inputs_and_unknown_ids(client, registered_user):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)

    assert _start(client, token, 5, 999999, 999999).status_code == 404
    assert _start(client, token, 4, resume_id, job_id).status_code == 422
    assert _start(client, token, 11, resume_id, job_id).status_code == 422
    assert client.get("/api/v1/interviews/999999", headers=_auth(token)).status_code == 404

    interview = _start(client, token, 5, resume_id, job_id).json()
    assert _answer(client, token, interview["id"], 999999).status_code == 404
    assert _answer(client, token, interview["id"], interview["questions"][0]["id"], "  ").status_code == 422


def test_ai_failure_returns_502(client, registered_user, monkeypatch):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)

    def _fail(data):
        raise InterviewGenerationError("The AI service is unavailable right now.")

    monkeypatch.setattr(generator, "generate_questions", _fail)
    response = _start(client, token, 5, resume_id, job_id)
    assert response.status_code == 502
    assert response.json()["detail"] == "AI service failed. Please try again."
