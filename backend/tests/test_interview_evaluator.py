import json
from types import SimpleNamespace

import pytest

from app.schemas.interview import QuestionCategory
from app.services.interviews import evaluator
from app.services.interviews.evaluator import EvaluationError, EvaluationInput, EvaluationQuestion


def _question(position: int, focus: str, answer: str | None = None) -> EvaluationQuestion:
    return EvaluationQuestion(
        position=position,
        category=list(QuestionCategory)[(position - 1) % 5],
        question=f"Question {position} about {focus}?",
        focus_skill=focus,
        answer=answer
        or "First I define the concept. Then I apply it to a project. The result improved latency by 30%.",
    )


def _input(count: int = 2) -> EvaluationInput:
    return EvaluationInput(
        job_title="Python Developer",
        job_description="Build Python services with SQL and Docker.",
        required_skills=["Python", "SQL"],
        questions=[_question(index, "SQL" if index % 2 else "Python") for index in range(1, count + 1)],
    )


def _answer(position: int) -> dict:
    return {
        "position": position,
        "score": 72,
        "technical_accuracy": 75,
        "relevance": 80,
        "completeness": 70,
        "clarity": 65,
        "strengths": ["Good explanation."],
        "weaknesses": ["Add trade-offs."],
        "suggested_improvement": "Explain the trade-offs.",
        "model_answer": "A strong answer defines the idea and gives an example.",
    }


def _draft(count: int = 2) -> dict:
    return {
        "overall_score": 72,
        "overall_summary": "Solid content-based answer review.",
        "overall_strengths": ["Clear examples."],
        "overall_weaknesses": ["Add trade-offs."],
        "suggested_improvements": ["Explain trade-offs."],
        "answer_evaluations": [_answer(index) for index in range(1, count + 1)],
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
        evaluator,
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

    monkeypatch.setattr(evaluator, "LLMClient", factory)
    return holder


def test_heuristic_evaluates_every_answer():
    draft, engine = evaluator.evaluate_answers(_input())
    assert engine == "heuristic"
    assert len(draft.answer_evaluations) == 2
    assert [item.position for item in draft.answer_evaluations] == [1, 2]
    assert draft.overall_score == int(sum(item.score for item in draft.answer_evaluations) / 2 + 0.5)
    for answer in draft.answer_evaluations:
        assert 0 <= answer.score <= 100
        for key in ("technical_accuracy", "relevance", "completeness", "clarity"):
            assert 0 <= getattr(answer, key) <= 100
        assert answer.strengths
        assert answer.weaknesses
        assert answer.suggested_improvement
        assert answer.model_answer


def test_heuristic_rewards_detailed_answers():
    data = _input(1)
    data.questions[0].answer = "SQL"
    short_draft, _ = evaluator.evaluate_answers(data)
    data.questions[0].answer = (
        "First I define SQL and explain joins. I used it in a project to combine "
        "customer and order tables. The result reduced report time by 30% and I "
        "considered indexes as a trade-off."
    )
    detailed_draft, _ = evaluator.evaluate_answers(data)
    assert detailed_draft.answer_evaluations[0].score > short_draft.answer_evaluations[0].score


def test_heuristic_makes_no_emotion_or_personality_claims():
    draft, _ = evaluator.evaluate_answers(_input())
    text = draft.model_dump_json().lower()
    for banned in ("emotion", "personality", "nervous", "mood", "sentiment"):
        assert banned not in text


def test_llm_valid_evaluation_is_validated(monkeypatch):
    holder = _enable_llm(monkeypatch, [json.dumps(_draft())])
    draft, engine = evaluator.evaluate_answers(_input())
    assert engine == "llm"
    assert holder["client"].calls == 1
    assert len(draft.answer_evaluations) == 2
    assert all(item.strengths and item.weaknesses for item in draft.answer_evaluations)


def test_llm_accepts_code_fenced_json(monkeypatch):
    _enable_llm(monkeypatch, ["```json\n" + json.dumps(_draft()) + "\n```"])
    draft, engine = evaluator.evaluate_answers(_input())
    assert engine == "llm"
    assert len(draft.answer_evaluations) == 2


def test_llm_retries_once(monkeypatch):
    holder = _enable_llm(monkeypatch, ["not json", json.dumps(_draft())])
    draft, engine = evaluator.evaluate_answers(_input())
    assert engine == "llm"
    assert holder["client"].calls == 2
    assert draft.overall_score == 72


def test_llm_wrong_positions_fail_after_retry(monkeypatch):
    payload = _draft()
    payload["answer_evaluations"][1]["position"] = 9
    holder = _enable_llm(monkeypatch, [json.dumps(payload), json.dumps(payload)])
    with pytest.raises(EvaluationError):
        evaluator.evaluate_answers(_input())
    assert holder["client"].calls == 2


def test_llm_missing_feedback_fails_after_retry(monkeypatch):
    payload = _draft()
    payload["answer_evaluations"][0]["strengths"] = []
    _enable_llm(monkeypatch, [json.dumps(payload), json.dumps(payload)])
    with pytest.raises(EvaluationError):
        evaluator.evaluate_answers(_input())


def test_llm_network_error_is_wrapped(monkeypatch):
    monkeypatch.setattr(
        evaluator,
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

    monkeypatch.setattr(evaluator, "LLMClient", _FailingClient)
    with pytest.raises(EvaluationError):
        evaluator.evaluate_answers(_input())
