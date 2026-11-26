"""Unit tests for AI-first interview question generation."""

import json
from types import SimpleNamespace

import pytest

from app.schemas.interview import QuestionCategory
from app.services.interviews import generator
from app.services.interviews.generator import InterviewInput

CATEGORIES = [item.value for item in QuestionCategory]


def _input(count: int = 5) -> InterviewInput:
    return InterviewInput(
        job_title="Python Developer",
        job_description="Build Python services with SQL and Docker.",
        required_skills=["Python", "SQL", "Docker"],
        resume_skills=["Python", "Docker"],
        projects=["Built a Random Forest classifier for customer churn"],
        missing_skills=["SQL"],
        match_score=70,
        question_count=count,
    )


def _payload(count: int = 5) -> dict:
    return {
        "questions": [
            {
                "category": CATEGORIES[index % len(CATEGORIES)],
                "question": f"Question number {index + 1}?",
                "focus_skill": "Python" if index % 2 == 0 else "",
            }
            for index in range(count)
        ]
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
        generator,
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

    monkeypatch.setattr(generator, "LLMClient", factory)
    return holder


def test_heuristic_generates_five_unique_questions():
    plan, engine = generator.generate_questions(_input())

    assert engine == "heuristic"
    assert len(plan.questions) == 5
    assert {item.category for item in plan.questions} == set(QuestionCategory)
    assert len({item.question for item in plan.questions}) == 5
    assert any("Random Forest" in item.question for item in plan.questions)
    assert any(item.focus_skill == "SQL" for item in plan.questions)


def test_heuristic_generates_ten_questions():
    plan, _ = generator.generate_questions(_input(10))
    assert len(plan.questions) == 10
    assert {item.category for item in plan.questions} == set(QuestionCategory)
    assert all(item.focus_skill for item in plan.questions)


def test_heuristic_handles_no_projects_or_skills():
    data = _input()
    data.projects = []
    data.missing_skills = []
    data.required_skills = []
    data.resume_skills = []
    plan, _ = generator.generate_questions(data)
    assert len(plan.questions) == 5
    assert all(item.focus_skill for item in plan.questions)


def test_llm_valid_plan_is_validated(monkeypatch):
    holder = _enable_llm(monkeypatch, [json.dumps(_payload())])
    plan, engine = generator.generate_questions(_input())
    assert engine == "llm"
    assert holder["client"].calls == 1
    assert len(plan.questions) == 5
    assert all(item.focus_skill for item in plan.questions)


def test_llm_accepts_code_fenced_json(monkeypatch):
    _enable_llm(monkeypatch, ["```json\n" + json.dumps(_payload()) + "\n```"])
    plan, engine = generator.generate_questions(_input())
    assert engine == "llm"
    assert len(plan.questions) == 5


def test_llm_retries_once_then_succeeds(monkeypatch):
    holder = _enable_llm(monkeypatch, ["not json", json.dumps(_payload())])
    plan, engine = generator.generate_questions(_input())
    assert engine == "llm"
    assert holder["client"].calls == 2
    assert len(plan.questions) == 5


def test_llm_wrong_count_fails_after_retry(monkeypatch):
    holder = _enable_llm(
        monkeypatch,
        [json.dumps(_payload(4)), json.dumps(_payload(4))],
    )
    with pytest.raises(generator.InterviewGenerationError):
        generator.generate_questions(_input())
    assert holder["client"].calls == 2


def test_llm_missing_category_fails_after_retry(monkeypatch):
    payload = _payload()
    for item in payload["questions"]:
        item["category"] = "technical"
    _enable_llm(monkeypatch, [json.dumps(payload), json.dumps(payload)])
    with pytest.raises(generator.InterviewGenerationError):
        generator.generate_questions(_input())


def test_llm_duplicate_questions_fail_after_retry(monkeypatch):
    payload = _payload()
    for item in payload["questions"]:
        item["question"] = "Same question?"
    _enable_llm(monkeypatch, [json.dumps(payload), json.dumps(payload)])
    with pytest.raises(generator.InterviewGenerationError):
        generator.generate_questions(_input())


def test_llm_network_error_is_wrapped(monkeypatch):
    monkeypatch.setattr(
        generator,
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
            from app.services.jobs.llm import LLMError

            raise LLMError("boom")

    monkeypatch.setattr(generator, "LLMClient", _FailingClient)
    with pytest.raises(generator.InterviewGenerationError):
        generator.generate_questions(_input())
