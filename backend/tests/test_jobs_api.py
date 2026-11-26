"""End-to-end tests for the job description analysis endpoints."""

from types import SimpleNamespace

import pytest

from app.services.jobs import analyzer
from app.services.jobs.llm import LLMError

JD_TEXT = """Senior Python Developer

Required Skills
Python, SQL, FastAPI, PostgreSQL

Preferred Qualifications
Docker, AWS

You should have 5+ years of experience building backend services.
Bachelor's degree in Computer Science.
Strong communication and teamwork skills.
"""


@pytest.fixture(autouse=True)
def _force_heuristic(monkeypatch):
    # Make API tests deterministic regardless of a developer's .env.
    monkeypatch.setattr(analyzer, "settings", SimpleNamespace(llm_enabled=False))


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _analyze(client, token: str, text: str = JD_TEXT):
    return client.post("/api/v1/jobs/analyze", headers=_auth(token), json={"text": text})


def _register(client, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Other User", "email": email, "password": "Passw0rd1"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_analyze_creates_job(client, registered_user):
    token = registered_user["access_token"]
    response = _analyze(client, token)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["job_title"] == "Senior Python Developer"
    assert body["analysis_engine"] == "heuristic"
    assert body["original_text"] == JD_TEXT.strip()
    assert {"Python", "SQL", "FastAPI", "PostgreSQL"} <= set(body["required_skills"])
    assert {"Docker", "AWS"} <= set(body["preferred_skills"])
    assert "AWS" in body["cloud_technologies"]
    assert "Docker" in body["tools"]
    assert "Communication" in body["soft_skills"]
    assert body["experience_requirements"]
    assert body["education_requirements"]


def test_analyze_requires_auth(client):
    response = client.post("/api/v1/jobs/analyze", json={"text": JD_TEXT})
    assert response.status_code == 401


def test_analyze_rejects_short_text(client, registered_user):
    response = _analyze(client, registered_user["access_token"], text="too short")
    assert response.status_code == 422


def test_analyze_rejects_oversized_text(client, registered_user):
    response = _analyze(client, registered_user["access_token"], text="a" * 20001)
    assert response.status_code == 422


def test_analyze_requires_body(client, registered_user):
    response = client.post(
        "/api/v1/jobs/analyze",
        headers=_auth(registered_user["access_token"]),
        json={},
    )
    assert response.status_code == 422


def test_list_and_detail(client, registered_user):
    token = registered_user["access_token"]

    first = _analyze(client, token).json()
    second = _analyze(
        client,
        token,
        text="Job Title: Data Analyst\nRequired: SQL, Python, Tableau\nPreferred: Power BI",
    ).json()

    listing = client.get("/api/v1/jobs", headers=_auth(token))
    assert listing.status_code == 200
    items = listing.json()
    assert len(items) == 2
    assert items[0]["id"] == second["id"]  # newest first
    assert items[0]["job_title"] == "Data Analyst"

    detail = client.get(f"/api/v1/jobs/{first['id']}", headers=_auth(token))
    assert detail.status_code == 200
    body = detail.json()
    assert body["original_text"] == JD_TEXT.strip()
    assert "Python" in body["required_skills"]


def test_list_and_detail_require_auth(client):
    assert client.get("/api/v1/jobs").status_code == 401
    assert client.get("/api/v1/jobs/1").status_code == 401


def test_cannot_access_another_users_job(client, registered_user):
    token_a = registered_user["access_token"]
    job = _analyze(client, token_a).json()

    token_b = _register(client, "jobother@example.com")["access_token"]

    assert client.get(f"/api/v1/jobs/{job['id']}", headers=_auth(token_b)).status_code == 404
    listing = client.get("/api/v1/jobs", headers=_auth(token_b))
    assert listing.status_code == 200
    assert listing.json() == []


def test_get_unknown_job_returns_404(client, registered_user):
    response = client.get(
        "/api/v1/jobs/999999", headers=_auth(registered_user["access_token"])
    )
    assert response.status_code == 404


def test_ai_failure_returns_502_and_persists_nothing(client, registered_user, monkeypatch):
    token = registered_user["access_token"]

    monkeypatch.setattr(
        analyzer,
        "settings",
        SimpleNamespace(
            llm_enabled=True,
            LLM_API_KEY="test-key",
            LLM_BASE_URL="http://example.invalid/v1",
            LLM_MODEL="test-model",
            LLM_TIMEOUT_SECONDS=5.0,
        ),
    )

    class _FailingClient:
        def __init__(self, *args, **kwargs):
            pass

        def complete_json(self, system_prompt: str, user_prompt: str) -> str:
            raise LLMError("upstream down")

    monkeypatch.setattr(analyzer, "LLMClient", _FailingClient)

    response = _analyze(client, token)
    assert response.status_code == 502
    assert response.json()["detail"] == "AI service failed. Please try again."

    listing = client.get("/api/v1/jobs", headers=_auth(token))
    assert listing.json() == []
