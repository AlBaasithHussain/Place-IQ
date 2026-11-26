from types import SimpleNamespace

import pytest

from app.services.interviews import evaluator, generator as interview_generator
from app.services.jobs import analyzer
from app.services.roadmaps import generator as roadmap_generator
from pdf_utils import make_pdf

RESUME_TEXT = """Alice Example
alice@example.com

Education
B.Tech in Information Technology, NIT Trichy, 2026

Skills
Python, Docker, Git

Projects
Built a Random Forest classifier for customer churn.

Experience
2 years of software development experience.
"""

JOB_TEXT = """Job Title: Python Developer

Required Skills
Python, SQL, Docker

Preferred Qualifications
Kubernetes

Soft skills: Communication

3+ years of experience
Bachelor's degree in Computer Science
"""


@pytest.fixture(autouse=True)
def _force_heuristic(monkeypatch):
    monkeypatch.setattr(analyzer, "settings", SimpleNamespace(llm_enabled=False))
    monkeypatch.setattr(interview_generator, "settings", SimpleNamespace(llm_enabled=False))
    monkeypatch.setattr(evaluator, "settings", SimpleNamespace(llm_enabled=False))
    monkeypatch.setattr(roadmap_generator, "settings", SimpleNamespace(llm_enabled=False))


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Dashboard User", "email": email, "password": "Passw0rd1"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_match(client, token: str):
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
    return {
        "resume_id": upload.json()["id"],
        "job_id": job.json()["id"],
        "analysis": match.json(),
    }


def test_dashboard_requires_auth(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 401


def test_empty_dashboard_returns_zeroed_state(client, registered_user):
    response = client.get(
        "/api/v1/dashboard", headers=_auth(registered_user["access_token"])
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["has_data"] is False
    assert body["overview"]["resume_score"] == 0
    assert body["overview"]["job_match_score"] == 0
    assert body["overview"]["interview_score"] == 0
    assert body["overview"]["skills_learned"] == 0
    assert body["readiness"]["score"] == 0
    assert len(body["readiness"]["components"]) == 5
    assert body["target_skills"]["total_jobs"] == 0
    assert body["target_skills"]["skills"] == []
    assert body["learning_progress"]["has_roadmap"] is False
    assert body["recent_jobs"] == []
    assert body["trends"]["match_scores"] == []


def test_dashboard_aggregates_user_activity(client, registered_user):
    token = registered_user["access_token"]
    created = _create_match(client, token)
    analysis = created["analysis"]

    roadmap_response = client.post(
        "/api/v1/roadmaps/generate",
        headers=_auth(token),
        json={"analysis_id": analysis["id"], "duration_days": 7, "hours_per_day": 2.0},
    )
    assert roadmap_response.status_code == 201, roadmap_response.text
    roadmap = roadmap_response.json()
    for task in roadmap["tasks"][:2]:
        response = client.patch(
            f"/api/v1/roadmaps/{roadmap['id']}/tasks/{task['id']}",
            headers=_auth(token),
            json={"completed": True},
        )
        assert response.status_code == 200, response.text

    interview_response = client.post(
        "/api/v1/interviews/start",
        headers=_auth(token),
        json={
            "resume_id": created["resume_id"],
            "job_id": created["job_id"],
            "question_count": 5,
        },
    )
    assert interview_response.status_code == 201, interview_response.text
    interview = interview_response.json()
    for question in interview["questions"]:
        response = client.post(
            f"/api/v1/interviews/{interview['id']}/answer",
            headers=_auth(token),
            json={
                "question_id": question["id"],
                "answer": (
                    "I define the approach, apply Python and SQL, explain Docker "
                    "deployment, and verify the result with tests."
                ),
            },
        )
        assert response.status_code == 200, response.text

    evaluation_response = client.post(
        f"/api/v1/interviews/{interview['id']}/evaluate", headers=_auth(token)
    )
    assert evaluation_response.status_code == 200, evaluation_response.text
    evaluation = evaluation_response.json()

    response = client.get("/api/v1/dashboard", headers=_auth(token))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["has_data"] is True
    assert body["overview"]["resume_file_name"] == "resume.pdf"
    assert body["overview"]["resume_score"] > 0
    assert body["overview"]["job_match_score"] == analysis["score"]
    assert body["overview"]["interview_score"] == evaluation["overall_score"]
    assert body["overview"]["skills_learned"] > 0

    components = body["readiness"]["components"]
    assert [item["key"] for item in components] == [
        "skill_match",
        "interview_performance",
        "technical_preparation",
        "resume_strength",
        "learning_progress",
    ]
    assert round(sum(item["contribution"] for item in components)) == body["readiness"]["score"]
    assert "30%" in body["readiness"]["formula"]
    assert body["target_skills"]["total_jobs"] == 1
    assert any(
        item["skill"] == "Python" and item["job_count"] == 1
        for item in body["target_skills"]["skills"]
    )

    assert body["skill_analysis"]["analysis_id"] == analysis["id"]
    assert body["skill_analysis"]["job_title"] == "Python Developer"
    assert body["learning_progress"]["has_roadmap"] is True
    assert body["learning_progress"]["duration_days"] == 7
    assert body["learning_progress"]["total_tasks"] == 7
    assert body["learning_progress"]["completed_tasks"] == 2
    assert body["learning_progress"]["remaining_tasks"] == 5
    assert body["learning_progress"]["progress_percentage"] > 0
    assert body["interview"]["sessions"] == 1
    assert body["interview"]["completed_sessions"] == 1
    assert body["interview"]["questions_attempted"] == 5
    assert body["interview"]["questions_total"] == 5
    assert body["interview"]["evaluated_sessions"] == 1
    assert body["interview"]["average_score"] == evaluation["overall_score"]
    assert body["interview"]["latest_score"] == evaluation["overall_score"]
    assert body["recent_jobs"][0]["job_title"] == "Python Developer"
    assert body["recent_jobs"][0]["match_score"] == analysis["score"]
    assert body["trends"]["match_scores"][0]["value"] == analysis["score"]
    assert body["trends"]["interview_scores"][0]["value"] == evaluation["overall_score"]


def test_dashboard_is_ownership_scoped(client, registered_user):
    owner_token = registered_user["access_token"]
    _create_match(client, owner_token)

    other = _register(client, "other-dashboard@example.com")
    response = client.get(
        "/api/v1/dashboard", headers=_auth(other["access_token"])
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["has_data"] is False
    assert body["overview"]["resume_score"] == 0
    assert body["overview"]["job_match_score"] == 0
    assert body["readiness"]["score"] == 0
    assert body["target_skills"]["total_jobs"] == 0
    assert body["recent_jobs"] == []
    assert body["skill_analysis"]["strong_skills"] == []
