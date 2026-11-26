"""End-to-end tests for resume ↔ job matching endpoints."""

from types import SimpleNamespace

import pytest

from app.services.jobs import analyzer
from pdf_utils import make_pdf

RESUME_TEXT = """Alice Example
alice@example.com

Education
B.Tech in Information Technology, NIT Trichy, 2025

Skills
Python, PostgreSQL, Git, Docker

Projects
Built a FastAPI service.

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


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Match User", "email": email, "password": "Passw0rd1"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _setup_resume_and_job(client, token: str):
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


def _match(client, token: str, resume_id: int, job_id: int):
    return client.post(
        "/api/v1/analysis/match",
        headers=_auth(token),
        json={"resume_id": resume_id, "job_id": job_id},
    )


def test_match_creates_result(client, registered_user):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)

    response = _match(client, token, resume_id, job_id)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["resume_id"] == resume_id
    assert body["job_id"] == job_id
    assert isinstance(body["score"], int)
    assert 0 <= body["score"] <= 100

    statuses = {item["skill"]: item["status"] for item in body["comparisons"]}
    assert statuses["Python"] == "match"
    assert statuses["SQL"] == "partial"
    assert statuses["Docker"] == "match"
    assert statuses["Git"] == "match"
    assert statuses["Communication"] == "missing"
    assert "SQL" in body["partial_skills"]
    assert "Communication" in body["missing_skills"]
    assert "Git" in body["bonus_skills"]
    assert body["breakdown"]["required_skills"]["weight"] == 0.7
    assert "70% required skills" in body["explanation"]


def test_get_analysis_and_auth(client, registered_user):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)
    created = _match(client, token, resume_id, job_id).json()

    response = client.get(f"/api/v1/analysis/{created['id']}", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["score"] == created["score"]
    assert response.json()["comparisons"] == created["comparisons"]

    assert client.get(f"/api/v1/analysis/{created['id']}").status_code == 401


def test_match_is_deterministic(client, registered_user):
    token = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token)

    first = _match(client, token, resume_id, job_id).json()
    second = _match(client, token, resume_id, job_id).json()
    assert first["score"] == second["score"]
    assert first["comparisons"] == second["comparisons"]
    assert first["breakdown"] == second["breakdown"]


def test_cannot_match_another_users_data(client, registered_user):
    token_a = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token_a)

    token_b = _register(client, "analysis-other@example.com")["access_token"]
    response = _match(client, token_b, resume_id, job_id)
    assert response.status_code == 404
    assert response.json()["detail"] == "Resume not found"

    resume_b, job_b = _setup_resume_and_job(client, token_b)
    response = _match(client, token_a, resume_b, job_b)
    assert response.status_code == 404


def test_cannot_read_another_users_analysis(client, registered_user):
    token_a = registered_user["access_token"]
    resume_id, job_id = _setup_resume_and_job(client, token_a)
    analysis_id = _match(client, token_a, resume_id, job_id).json()["id"]

    token_b = _register(client, "analysis-reader@example.com")["access_token"]
    assert client.get(
        f"/api/v1/analysis/{analysis_id}", headers=_auth(token_b)
    ).status_code == 404


def test_missing_ids_return_404(client, registered_user):
    token = registered_user["access_token"]
    assert _match(client, token, 999999, 999999).status_code == 404


def test_invalid_ids_return_422(client, registered_user):
    token = registered_user["access_token"]
    assert _match(client, token, 0, 1).status_code == 422
    assert _match(client, token, 1, -1).status_code == 422


def test_unknown_analysis_returns_404(client, registered_user):
    response = client.get(
        "/api/v1/analysis/999999",
        headers=_auth(registered_user["access_token"]),
    )
    assert response.status_code == 404
