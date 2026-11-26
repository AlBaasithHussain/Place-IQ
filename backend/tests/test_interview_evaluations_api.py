import json
from types import SimpleNamespace

import pytest

from app.schemas.interview import InterviewEvaluationDraft
from app.services.interviews import evaluator, generator
from app.services.interviews.evaluator import EvaluationError
from app.services.jobs import analyzer
from pdf_utils import make_pdf

RESUME_TEXT = """Alice Example
alice@example.com

Education
B.Tech in Information Technology, NIT Trichy, 2026

Skills
Python, Docker

Projects
Built a Random Forest classifier for customer churn.

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
    monkeypatch.setattr(evaluator, "settings", SimpleNamespace(llm_enabled=False))


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup(client, token: str) -> tuple[int, int]:
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


def _start(client, token: str) -> dict:
    resume_id, job_id = _setup(client, token)
    response = client.post(
        "/api/v1/interviews/start",
        headers=_auth(token),
        json={"resume_id": resume_id, "job_id": job_id, "question_count": 5},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _complete(client, token: str) -> dict:
    interview = _start(client, token)
    for question in interview["questions"]:
        response = client.post(
            f"/api/v1/interviews/{interview['id']}/answer",
            headers=_auth(token),
            json={
                "question_id": question["id"],
                "answer": (
                    "First I define the approach. Then I apply it to my project. "
                    "The result improved latency by 30% and I considered trade-offs."
                ),
            },
        )
        assert response.status_code == 200, response.text
    return interview


def _draft(count: int) -> InterviewEvaluationDraft:
    return InterviewEvaluationDraft.model_validate(
        {
            "overall_score": 72,
            "overall_summary": "Solid content-based feedback.",
            "overall_strengths": ["Clear examples."],
            "overall_weaknesses": ["Add trade-offs."],
            "suggested_improvements": ["Explain trade-offs."],
            "answer_evaluations": [
                {
                    "position": index,
                    "score": 72,
                    "technical_accuracy": 75,
                    "relevance": 80,
                    "completeness": 70,
                    "clarity": 65,
                    "strengths": ["Good explanation."],
                    "weaknesses": ["Add trade-offs."],
                    "suggested_improvement": "Explain the trade-offs.",
                    "model_answer": "Define the idea and give a concrete example.",
                }
                for index in range(1, count + 1)
            ],
        }
    )


def test_evaluate_requires_completed_interview(client, registered_user):
    token = registered_user["access_token"]
    interview = _start(client, token)

    response = client.post(
        f"/api/v1/interviews/{interview['id']}/evaluate", headers=_auth(token)
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Interview must be completed before evaluation"

    results = client.get(
        f"/api/v1/interviews/{interview['id']}/results", headers=_auth(token)
    )
    assert results.status_code == 404


def test_evaluate_and_get_results(client, registered_user):
    token = registered_user["access_token"]
    interview = _complete(client, token)

    before = client.get(
        f"/api/v1/interviews/{interview['id']}", headers=_auth(token)
    ).json()
    assert before["has_evaluation"] is False

    response = client.post(
        f"/api/v1/interviews/{interview['id']}/evaluate", headers=_auth(token)
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["interview_id"] == interview["id"]
    assert body["job_title"] == "Python Developer"
    assert body["generation_engine"] == "heuristic"
    assert 0 <= body["overall_score"] <= 100
    assert body["overall_summary"]
    assert body["overall_strengths"]
    assert body["overall_weaknesses"]
    assert body["suggested_improvements"]
    assert body["question_count"] == 5
    assert body["evaluated_answer_count"] == 5
    assert [item["position"] for item in body["answer_evaluations"]] == [1, 2, 3, 4, 5]

    for item in body["answer_evaluations"]:
        assert item["question"]
        assert item["answer"]
        assert item["focus_skill"]
        for key in ("technical_accuracy", "relevance", "completeness", "clarity"):
            assert 0 <= item[key] <= 100
        assert item["strengths"]
        assert item["weaknesses"]
        assert item["suggested_improvement"]
        assert item["model_answer"]

    assert not any(
        term in json.dumps(body).lower()
        for term in ("emotion", "personality", "nervous", "mood", "sentiment")
    )

    results = client.get(
        f"/api/v1/interviews/{interview['id']}/results", headers=_auth(token)
    )
    assert results.status_code == 200
    assert results.json()["id"] == body["id"]

    after = client.get(
        f"/api/v1/interviews/{interview['id']}", headers=_auth(token)
    ).json()
    assert after["has_evaluation"] is True


def test_evaluate_is_idempotent(client, registered_user, monkeypatch):
    token = registered_user["access_token"]
    interview = _complete(client, token)

    first = client.post(
        f"/api/v1/interviews/{interview['id']}/evaluate", headers=_auth(token)
    )
    assert first.status_code == 200

    def _must_not_run(data):
        pytest.fail("Evaluation should not run twice")

    monkeypatch.setattr(evaluator, "evaluate_answers", _must_not_run)
    second = client.post(
        f"/api/v1/interviews/{interview['id']}/evaluate", headers=_auth(token)
    )
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["overall_score"] == first.json()["overall_score"]


def test_evaluation_ownership(client, registered_user):
    token_a = registered_user["access_token"]
    interview = _complete(client, token_a)
    client.post(f"/api/v1/interviews/{interview['id']}/evaluate", headers=_auth(token_a))

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Other User",
            "email": "evaluation-other@example.com",
            "password": "Passw0rd1",
        },
    )
    token_b = response.json()["access_token"]

    assert client.post(
        f"/api/v1/interviews/{interview['id']}/evaluate", headers=_auth(token_b)
    ).status_code == 404
    assert client.get(
        f"/api/v1/interviews/{interview['id']}/results", headers=_auth(token_b)
    ).status_code == 404


def test_ai_evaluation_failure_returns_502(client, registered_user, monkeypatch):
    token = registered_user["access_token"]
    interview = _complete(client, token)

    def _fail(data):
        raise EvaluationError("The AI evaluation service is unavailable right now.")

    monkeypatch.setattr(evaluator, "evaluate_answers", _fail)
    response = client.post(
        f"/api/v1/interviews/{interview['id']}/evaluate", headers=_auth(token)
    )
    assert response.status_code == 502
    assert response.json()["detail"] == "AI service failed. Please try again."


def test_ai_evaluation_result_is_persisted(client, registered_user, monkeypatch):
    token = registered_user["access_token"]
    interview = _complete(client, token)
    draft = _draft(5)

    monkeypatch.setattr(evaluator, "evaluate_answers", lambda data: (draft, "llm"))
    response = client.post(
        f"/api/v1/interviews/{interview['id']}/evaluate", headers=_auth(token)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["generation_engine"] == "llm"
    assert body["overall_score"] == 72
    assert len(body["answer_evaluations"]) == 5

    results = client.get(
        f"/api/v1/interviews/{interview['id']}/results", headers=_auth(token)
    )
    assert results.status_code == 200
    assert results.json()["generation_engine"] == "llm"
