"""Unit tests for the job-description analyzer (heuristic + AI paths)."""

import json
from types import SimpleNamespace

import pytest

from app.services.jobs import analyzer
from app.services.jobs.llm import LLMError

SAMPLE = """Senior Python Developer

About us
We build data products.

Required Skills
Python, SQL, FastAPI, PostgreSQL

Preferred Qualifications
Docker, AWS

You should have 5+ years of experience building backend services.
Bachelor's degree in Computer Science or related field.
Strong communication and teamwork skills.
"""

VALID_PAYLOAD = {
    "job_title": "Python Developer",
    "required_skills": ["Python", " SQL ", "Python"],
    "preferred_skills": ["Docker", "AWS"],
    "programming_languages": ["Python"],
    "frameworks": ["FastAPI"],
    "databases": ["PostgreSQL"],
    "cloud_technologies": ["AWS"],
    "tools": ["Docker"],
    "soft_skills": ["Communication"],
    "experience_requirements": ["3+ years"],
    "education_requirements": ["Bachelor's degree"],
}


class _FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        return self.responses.pop(0)


def _enable_llm(monkeypatch, responses):
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
    holder: dict = {}

    def factory(*args, **kwargs):
        client = _FakeClient(responses)
        holder["client"] = client
        return client

    monkeypatch.setattr(analyzer, "LLMClient", factory)
    return holder


# ---------------------------- heuristic ----------------------------
def test_heuristic_extracts_title():
    result = analyzer.analyze_heuristic(SAMPLE)
    assert result.job_title == "Senior Python Developer"


def test_heuristic_extracts_categories():
    result = analyzer.analyze_heuristic(SAMPLE)
    assert {"Python", "SQL"} <= set(result.programming_languages)
    assert "FastAPI" in result.frameworks
    assert "PostgreSQL" in result.databases
    assert "AWS" in result.cloud_technologies
    assert "Docker" in result.tools
    assert "AWS" not in result.tools
    assert {"Communication", "Teamwork"} <= set(result.soft_skills)


def test_heuristic_separates_required_and_preferred():
    result = analyzer.analyze_heuristic(SAMPLE)
    assert {"Python", "SQL", "FastAPI", "PostgreSQL"} <= set(result.required_skills)
    assert {"Docker", "AWS"} <= set(result.preferred_skills)
    assert set(result.required_skills).isdisjoint(result.preferred_skills)


def test_heuristic_extracts_experience_and_education():
    result = analyzer.analyze_heuristic(SAMPLE)
    assert any("5+ years" in item for item in result.experience_requirements)
    assert any("Bachelor" in item for item in result.education_requirements)


def test_heuristic_reads_job_title_label():
    result = analyzer.analyze_heuristic("Job Title: Backend Engineer\nRequirements: Python")
    assert result.job_title == "Backend Engineer"


def test_heuristic_title_falls_back_to_first_line():
    result = analyzer.analyze_heuristic(
        "We are a growing startup.\n\nMore details about the role will follow."
    )
    assert result.job_title == "We are a growing startup."


# ------------------------------- AI -------------------------------
def test_heuristic_engine_selected_without_key(monkeypatch):
    monkeypatch.setattr(analyzer, "settings", SimpleNamespace(llm_enabled=False))
    result, engine = analyzer.analyze_job_description(SAMPLE)
    assert engine == "heuristic"
    assert result.job_title == "Senior Python Developer"


def test_llm_valid_json_is_validated_and_engine_reported(monkeypatch):
    holder = _enable_llm(monkeypatch, [json.dumps(VALID_PAYLOAD)])
    result, engine = analyzer.analyze_job_description(SAMPLE)

    assert engine == "llm"
    assert holder["client"].calls == 1
    assert result.job_title == "Python Developer"
    # duplicates and surrounding whitespace are normalised away
    assert result.required_skills == ["Python", "SQL"]


def test_llm_accepts_code_fenced_json(monkeypatch):
    fenced = "```json\n" + json.dumps(VALID_PAYLOAD) + "\n```"
    _enable_llm(monkeypatch, [fenced])
    result, engine = analyzer.analyze_job_description(SAMPLE)
    assert engine == "llm"
    assert result.job_title == "Python Developer"


def test_llm_retries_once_then_succeeds(monkeypatch):
    holder = _enable_llm(monkeypatch, ["not json at all", json.dumps(VALID_PAYLOAD)])
    result, engine = analyzer.analyze_job_description(SAMPLE)
    assert engine == "llm"
    assert holder["client"].calls == 2
    assert result.job_title == "Python Developer"


def test_llm_fails_after_two_invalid_replies(monkeypatch):
    _enable_llm(monkeypatch, ["nope", "still nope"])
    with pytest.raises(analyzer.JobAnalysisError):
        analyzer.analyze_job_description(SAMPLE)


def test_llm_rejects_schema_mismatch(monkeypatch):
    bad = json.dumps({"job_title": "", "required_skills": "Python"})
    _enable_llm(monkeypatch, [bad, bad])
    with pytest.raises(analyzer.JobAnalysisError):
        analyzer.analyze_job_description(SAMPLE)


def test_llm_network_error_is_wrapped(monkeypatch):
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
            raise LLMError("connection refused")

    monkeypatch.setattr(analyzer, "LLMClient", _FailingClient)
    with pytest.raises(analyzer.JobAnalysisError):
        analyzer.analyze_job_description(SAMPLE)
