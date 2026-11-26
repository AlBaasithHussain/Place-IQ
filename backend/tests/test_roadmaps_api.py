"""End-to-end tests for personalised roadmap endpoints."""

from types import SimpleNamespace

import pytest

from app.services.jobs import analyzer
from app.services.roadmaps import generator
from app.services.roadmaps.generator import RoadmapGenerationError
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
    monkeypatch.setattr(generator, "settings", SimpleNamespace(llm_enabled=False))


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Roadmap User", "email": email, "password": "Passw0rd1"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _setup_match(client, token: str) -> dict:
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

    match = client.post(
        "/api/v1/analysis/match",
        headers=_auth(token),
        json={"resume_id": upload.json()["id"], "job_id": job.json()["id"]},
    )
    assert match.status_code == 201, match.text
    return match.json()


def _generate(client, token: str, analysis_id: int, days: int = 7, hours: float = 2.0):
    return client.post(
        "/api/v1/roadmaps/generate",
        headers=_auth(token),
        json={
            "analysis_id": analysis_id,
            "duration_days": days,
            "hours_per_day": hours,
        },
    )


def test_generate_builds_seven_day_roadmap(client, registered_user):
    token = registered_user["access_token"]
    match = _setup_match(client, token)

    response = _generate(client, token, match["id"])
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["analysis_id"] == match["id"]
    assert body["match_score"] == match["score"]
    assert body["job_title"] == "Python Developer"
    assert body["generation_engine"] == "heuristic"
    assert body["duration_days"] == 7
    assert body["hours_per_day"] == 2.0
    assert body["progress_percentage"] == 0
    assert body["completed_count"] == 0
    assert body["total_estimated_minutes"] == 840

    assert {"SQL", "Communication"} <= set(body["priority_skills"])
    assert [task["day"] for task in body["tasks"]] == list(range(1, 8))
    assert all(task["estimated_minutes"] == 120 for task in body["tasks"])
    assert all(task["learning_topics"] for task in body["tasks"])
    assert all(task["practice_tasks"] for task in body["tasks"])
    assert all(task["mini_project"] for task in body["tasks"])
    assert any(task["priority"] == "high" for task in body["tasks"])
    assert any(task["priority"] == "low" for task in body["tasks"])
    assert "70% required skills" in match["explanation"]


def test_get_and_list_roadmap_with_auth(client, registered_user):
    token = registered_user["access_token"]
    match = _setup_match(client, token)
    created = _generate(client, token, match["id"]).json()

    response = client.get(f"/api/v1/roadmaps/{created['id']}", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["tasks"] == created["tasks"]

    listing = client.get("/api/v1/roadmaps", headers=_auth(token))
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["id"] == created["id"]

    assert client.get(f"/api/v1/roadmaps/{created['id']}").status_code == 401
    assert client.get("/api/v1/roadmaps").status_code == 401


def test_task_completion_updates_progress(client, registered_user):
    token = registered_user["access_token"]
    match = _setup_match(client, token)
    roadmap = _generate(client, token, match["id"]).json()
    task_id = roadmap["tasks"][0]["id"]

    response = client.patch(
        f"/api/v1/roadmaps/{roadmap['id']}/tasks/{task_id}",
        headers=_auth(token),
        json={"completed": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["completed_count"] == 1
    assert body["progress_percentage"] == 14
    assert body["tasks"][0]["completed"] is True
    assert body["tasks"][0]["completed_at"] is not None

    response = client.patch(
        f"/api/v1/roadmaps/{roadmap['id']}/tasks/{task_id}",
        headers=_auth(token),
        json={"completed": False},
    )
    assert response.status_code == 200
    assert response.json()["progress_percentage"] == 0
    assert response.json()["tasks"][0]["completed_at"] is None


def test_fourteen_day_roadmap(client, registered_user):
    token = registered_user["access_token"]
    match = _setup_match(client, token)

    response = _generate(client, token, match["id"], days=14, hours=1.0)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["duration_days"] == 14
    assert len(body["tasks"]) == 14
    assert all(task["estimated_minutes"] == 60 for task in body["tasks"])
    assert body["tasks"][-1]["title"] == "Mini Project & Practice Interview"


def test_cannot_use_another_users_analysis_or_roadmap(client, registered_user):
    token_a = registered_user["access_token"]
    match = _setup_match(client, token_a)
    roadmap = _generate(client, token_a, match["id"]).json()

    token_b = _register(client, "roadmap-other@example.com")["access_token"]
    assert _generate(client, token_b, match["id"]).status_code == 404
    assert client.get(
        f"/api/v1/roadmaps/{roadmap['id']}", headers=_auth(token_b)
    ).status_code == 404
    assert client.patch(
        f"/api/v1/roadmaps/{roadmap['id']}/tasks/{roadmap['tasks'][0]['id']}",
        headers=_auth(token_b),
        json={"completed": True},
    ).status_code == 404


def test_invalid_inputs_and_unknown_ids(client, registered_user):
    token = registered_user["access_token"]
    match = _setup_match(client, token)

    assert _generate(client, token, 999999).status_code == 404
    assert _generate(client, token, 0).status_code == 422
    assert _generate(client, token, match["id"], days=10).status_code == 422
    assert _generate(client, token, match["id"], hours=0).status_code == 422
    assert client.get("/api/v1/roadmaps/999999", headers=_auth(token)).status_code == 404


def test_unknown_task_returns_404(client, registered_user):
    token = registered_user["access_token"]
    match = _setup_match(client, token)
    roadmap = _generate(client, token, match["id"]).json()

    response = client.patch(
        f"/api/v1/roadmaps/{roadmap['id']}/tasks/999999",
        headers=_auth(token),
        json={"completed": True},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_ai_failure_returns_502(client, registered_user, monkeypatch):
    token = registered_user["access_token"]
    match = _setup_match(client, token)

    def _fail(data):
        raise RoadmapGenerationError("The AI service is unavailable right now.")

    monkeypatch.setattr(generator, "generate_roadmap", _fail)
    response = _generate(client, token, match["id"])
    assert response.status_code == 502
    assert response.json()["detail"] == "AI service failed. Please try again."
