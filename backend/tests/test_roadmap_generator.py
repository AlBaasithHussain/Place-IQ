"""Unit tests for AI-first roadmap generation and its local fallback."""

import json
from types import SimpleNamespace

import pytest

from app.schemas.roadmap import PriorityLevel
from app.services.roadmaps import generator
from app.services.roadmaps.generator import RoadmapInput


def _input(days: int = 7, hours: float = 2.0) -> RoadmapInput:
    return RoadmapInput(
        job_title="Python Developer",
        required_skills=["Python", "SQL"],
        missing_skills=["SQL"],
        partial_skills=[],
        resume_skills=["Python"],
        match_score=70,
        duration_days=days,
        hours_per_day=hours,
        priority_map={"SQL": PriorityLevel.HIGH},
    )


def _payload(days: int, minutes: int = 120) -> dict:
    return {
        "priority_skills": ["SQL"],
        "summary": "Focused SQL practice",
        "days": [
            {
                "day": day,
                "title": f"SQL topic {day}",
                "priority": "high",
                "estimated_minutes": minutes,
                "learning_topics": [f"Topic {day}"],
                "practice_tasks": [f"Exercise {day}"],
                "mini_project": f"Project {day}",
            }
            for day in range(1, days + 1)
        ],
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


def test_daily_minutes_rounds_to_nearest_five():
    assert generator.daily_minutes(_input(hours=1.02)) == 60
    assert generator.daily_minutes(_input(hours=0.25)) == 15


def test_heuristic_builds_seven_day_plan():
    plan, engine = generator.generate_roadmap(_input())

    assert engine == "heuristic"
    assert plan.priority_skills == ["SQL"]
    assert [item.day for item in plan.days] == list(range(1, 8))
    assert all(item.estimated_minutes == 120 for item in plan.days)
    assert all(item.priority == PriorityLevel.HIGH for item in plan.days)
    assert "SQL JOIN" in plan.days[0].learning_topics
    assert plan.days[-1].title == "Mini Project & Practice Interview"


def test_heuristic_builds_fourteen_day_plan():
    plan, engine = generator.generate_roadmap(_input(days=14))
    assert engine == "heuristic"
    assert len(plan.days) == 14
    assert plan.days[-1].day == 14


def test_heuristic_handles_no_missing_skills():
    data = _input()
    data.missing_skills = []
    data.partial_skills = []
    plan, _ = generator.generate_roadmap(data)
    assert plan.priority_skills == ["general preparation"]
    assert len(plan.days) == 7


def test_llm_plan_is_validated_and_normalised(monkeypatch):
    payload = _payload(7)
    payload["days"][0]["estimated_minutes"] = 999
    holder = _enable_llm(monkeypatch, [json.dumps(payload)])

    plan, engine = generator.generate_roadmap(_input())

    assert engine == "llm"
    assert holder["client"].calls == 1
    assert plan.summary == "Focused SQL practice"
    assert plan.days[0].estimated_minutes == 120
    assert all(item.day == index for index, item in enumerate(plan.days, start=1))
    assert all(item.priority == PriorityLevel.HIGH for item in plan.days)


def test_llm_accepts_code_fenced_json(monkeypatch):
    payload = _payload(7)
    _enable_llm(monkeypatch, ["```json\n" + json.dumps(payload) + "\n```"])
    plan, engine = generator.generate_roadmap(_input())
    assert engine == "llm"
    assert len(plan.days) == 7


def test_llm_retries_once_then_succeeds(monkeypatch):
    holder = _enable_llm(
        monkeypatch,
        ["not json", json.dumps(_payload(7))],
    )
    plan, engine = generator.generate_roadmap(_input())
    assert engine == "llm"
    assert holder["client"].calls == 2
    assert len(plan.days) == 7


def test_llm_wrong_day_count_fails_after_retry(monkeypatch):
    holder = _enable_llm(
        monkeypatch,
        [json.dumps(_payload(6)), json.dumps(_payload(6))],
    )
    with pytest.raises(generator.RoadmapGenerationError):
        generator.generate_roadmap(_input())
    assert holder["client"].calls == 2


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
    with pytest.raises(generator.RoadmapGenerationError):
        generator.generate_roadmap(_input())
