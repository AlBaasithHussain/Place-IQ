import json
import re
from dataclasses import dataclass

from app.core.config import settings
from app.schemas.interview import (
    AnswerEvaluationDraft,
    InterviewEvaluationDraft,
    QuestionCategory,
)
from app.services.jobs.llm import LLMClient, LLMError

SYSTEM_PROMPT = (
    "You are a fair mock interview answer evaluator. Evaluate only the written "
    "answer content. Reply with ONLY a single valid JSON object - no prose and no "
    "markdown. The object must have exactly these keys: overall_score (integer "
    "0-100), overall_summary (string), overall_strengths (1-3 strings), "
    "overall_weaknesses (1-3 strings), suggested_improvements (1-3 strings), "
    "answer_evaluations (array). Each answer object must have exactly these keys: "
    "position (integer matching the supplied position), score (0-100), "
    "technical_accuracy (0-100), relevance (0-100), completeness (0-100), "
    "clarity (0-100), strengths (1-3 strings), weaknesses (1-3 strings), "
    "suggested_improvement (string), model_answer (string). Score only technical "
    "accuracy, relevance, completeness and clarity. Do not assess or report "
    "emotions, personality traits, mood, sentiment, nervousness or any "
    "psychological characteristic. Do not invent question IDs; use the supplied "
    "position numbers only."
)

REPAIR_INSTRUCTION = (
    "Your previous reply was not valid JSON for the evaluation schema. Reply "
    "again with ONLY the corrected JSON object, one entry per supplied position, "
    "all required keys, and no code fences."
)

STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "been",
    "being",
    "could",
    "describe",
    "did",
    "does",
    "explain",
    "have",
    "how",
    "into",
    "just",
    "more",
    "most",
    "other",
    "over",
    "really",
    "some",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "very",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
}


class EvaluationError(Exception):
    pass


@dataclass
class EvaluationQuestion:
    position: int
    category: QuestionCategory
    question: str
    focus_skill: str
    answer: str


@dataclass
class EvaluationInput:
    job_title: str
    job_description: str
    required_skills: list[str]
    questions: list[EvaluationQuestion]


def _strip_code_fences(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[A-Za-z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    return text.strip()


def _user_prompt(data: EvaluationInput) -> str:
    lines = [
        "Evaluate these mock interview answers.",
        f"Target role: {data.job_title}",
        f"Job description: {data.job_description[:3000]}",
        f"Required skills: {', '.join(data.required_skills) or 'none listed'}",
        f"Return exactly {len(data.questions)} answer evaluations.",
    ]
    for item in data.questions:
        lines.append(
            f"Position {item.position} | {item.category.value} | focus: {item.focus_skill}\n"
            f"Question: {item.question[:1000]}\n"
            f"Answer: {item.answer[:4000]}"
        )
    return "\n\n".join(lines)


def _validate(content: str, data: EvaluationInput) -> InterviewEvaluationDraft:
    parsed = json.loads(_strip_code_fences(content))
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON must be an object")
    draft = InterviewEvaluationDraft.model_validate(parsed)
    actual = sorted(item.position for item in draft.answer_evaluations)
    expected = sorted(item.position for item in data.questions)
    if actual != expected:
        raise ValueError("evaluation positions must match the questions")
    return draft


def generate_with_llm(data: EvaluationInput) -> InterviewEvaluationDraft:
    client = LLMClient(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    prompt = _user_prompt(data)
    prompts = [prompt, prompt + "\n\n" + REPAIR_INSTRUCTION]
    try:
        for attempt in prompts:
            try:
                content = client.complete_json(SYSTEM_PROMPT, attempt)
            except LLMError as exc:
                raise EvaluationError(
                    "The AI evaluation service is unavailable right now. Please try again."
                ) from exc
            try:
                return _validate(content, data)
            except ValueError:
                continue
    except EvaluationError:
        raise
    raise EvaluationError("The AI returned an evaluation that failed validation.")


def _clamp(value: float) -> int:
    return max(0, min(100, int(value)))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.]+", text.lower())


def _mentions(text: str, term: str) -> bool:
    needle = term.strip().lower()
    if not needle:
        return False
    haystack = text.lower()
    if needle in haystack:
        return True
    return needle in " ".join(_tokens(haystack))


def _score_answer(item: EvaluationQuestion, data: EvaluationInput) -> dict:
    answer = item.answer.strip()
    lowered = answer.lower()
    words = _tokens(answer)
    word_count = len(words)
    sentence_count = max(1, answer.count(".") + answer.count("!") + answer.count("?"))
    structure_markers = ("first", "then", "because", "step", "result", "trade-off", "however", "example")
    result_markers = ("result", "outcome", "impact", "improved", "reduced", "achieved")
    has_structure = any(marker in lowered for marker in structure_markers)
    has_result = any(marker in lowered for marker in result_markers)

    terms = [item.focus_skill, data.job_title, *data.required_skills]
    term_hits = sum(1 for term in terms if _mentions(answer, term))
    question_terms = [word for word in _tokens(item.question) if word not in STOPWORDS and len(word) > 2]
    overlap = 0.0
    if question_terms:
        overlap = sum(1 for word in question_terms if word in words) / len(question_terms)

    technical = 30 + min(45, term_hits * 15) + min(20, word_count) + (10 if has_structure else 0)
    relevance = 35 + min(40, overlap * 100) + (15 if _mentions(answer, item.focus_skill) else 0)
    if overlap > 0.3:
        relevance += 10
    completeness = 25 + min(45, word_count * 1.5)
    if has_structure:
        completeness += 10
    if has_result:
        completeness += 10
    if has_structure and word_count > 40:
        completeness += 10
    clarity = 35 + min(35, word_count) + (10 if sentence_count > 1 else 0) + (10 if has_structure else 0)

    scores = {
        "technical_accuracy": _clamp(technical),
        "relevance": _clamp(relevance),
        "completeness": _clamp(completeness),
        "clarity": _clamp(clarity),
    }
    scores["score"] = _clamp(sum(scores.values()) / 4)
    return scores


def _strengths(item: EvaluationQuestion, scores: dict) -> list[str]:
    result: list[str] = []
    if scores["technical_accuracy"] >= 70:
        result.append(f"Covers useful technical ideas around {item.focus_skill}.")
    if scores["relevance"] >= 70:
        result.append("Stays focused on what the question asked.")
    if scores["clarity"] >= 70:
        result.append("Presents the answer in a clear, readable structure.")
    if not result:
        result.append("Provides a written response that can be built on.")
    return result[:3]


def _weaknesses(item: EvaluationQuestion, scores: dict) -> list[str]:
    result: list[str] = []
    if scores["technical_accuracy"] < 70:
        result.append(f"Add more precise detail about {item.focus_skill} and how it works.")
    if scores["relevance"] < 70:
        result.append("Tie the answer more directly to the question and target role.")
    if scores["completeness"] < 70:
        result.append("Add context, actions taken, and the outcome or result.")
    if scores["clarity"] < 70:
        result.append("Use shorter sentences and explicit steps to improve readability.")
    if not result:
        result.append("Add measurable outcomes or trade-offs to strengthen the answer.")
    return result[:3]


def _improvement(item: EvaluationQuestion, scores: dict) -> str:
    if scores["technical_accuracy"] < 70:
        return f"Define {item.focus_skill}, give a concrete use case, and name one trade-off."
    if scores["relevance"] < 70:
        return "Restate the question's core ask, then answer it with role-specific examples."
    if scores["completeness"] < 70:
        return "Use situation, action, result and learning so the answer feels complete."
    return "Add a measurable result and one follow-up trade-off to make the answer stronger."


def _model_answer(item: EvaluationQuestion) -> str:
    focus = item.focus_skill or "the role"
    if item.category == QuestionCategory.TECHNICAL:
        return (
            f"Define {focus}, explain when you would use it, walk through a concrete "
            "example, and finish with trade-offs, failure modes or validation steps."
        )
    if item.category == QuestionCategory.PROJECT:
        return (
            "Use situation, task, action and result: describe the project goal, your "
            "specific contribution, the technical choices, the measurable outcome and "
            "what you would improve next."
        )
    if item.category == QuestionCategory.BEHAVIORAL:
        return (
            "Describe the situation, your responsibility, the action you took, the "
            "result, and what you learned. Keep it specific and avoid blaming others."
        )
    if item.category == QuestionCategory.PROBLEM:
        return (
            "Clarify constraints, break the problem into steps, propose an approach, "
            "discuss trade-offs, and explain how you would validate the result."
        )
    return (
        f"Connect your skills and projects to the {focus} role, give one specific "
        "strength with evidence, and name one area you are actively improving."
    )


def _mean(values: list[int]) -> int:
    if not values:
        return 0
    return int(sum(values) / len(values) + 0.5)


def _label(key: str) -> str:
    return {
        "technical_accuracy": "technical accuracy",
        "relevance": "relevance",
        "completeness": "completeness",
        "clarity": "clarity",
    }[key]


def generate_heuristic(data: EvaluationInput) -> InterviewEvaluationDraft:
    answers: list[AnswerEvaluationDraft] = []
    for item in data.questions:
        scores = _score_answer(item, data)
        answers.append(
            AnswerEvaluationDraft(
                position=item.position,
                score=scores["score"],
                technical_accuracy=scores["technical_accuracy"],
                relevance=scores["relevance"],
                completeness=scores["completeness"],
                clarity=scores["clarity"],
                strengths=_strengths(item, scores),
                weaknesses=_weaknesses(item, scores),
                suggested_improvement=_improvement(item, scores),
                model_answer=_model_answer(item),
            )
        )

    criterion_means = {
        key: _mean([getattr(answer, key) for answer in answers])
        for key in ("technical_accuracy", "relevance", "completeness", "clarity")
    }
    best_key = max(criterion_means, key=criterion_means.get)
    worst_key = min(criterion_means, key=criterion_means.get)
    overall_summary = (
        f"Content-based review across {len(answers)} answers. Strongest criterion: "
        f"{_label(best_key)} ({criterion_means[best_key]}). Biggest gap: "
        f"{_label(worst_key)} ({criterion_means[worst_key]})."
    )

    strength_counts: dict[str, int] = {}
    weakness_counts: dict[str, int] = {}
    for answer in answers:
        for text in answer.strengths:
            strength_counts[text] = strength_counts.get(text, 0) + 1
        for text in answer.weaknesses:
            weakness_counts[text] = weakness_counts.get(text, 0) + 1
    overall_strengths = sorted(strength_counts, key=lambda text: (-strength_counts[text], text))[:3]
    overall_weaknesses = sorted(weakness_counts, key=lambda text: (-weakness_counts[text], text))[:3]

    suggestions: list[str] = []
    for answer in answers:
        text = answer.suggested_improvement
        if text not in suggestions:
            suggestions.append(text)
        if len(suggestions) == 3:
            break

    return InterviewEvaluationDraft(
        overall_score=_mean([answer.score for answer in answers]),
        overall_summary=overall_summary,
        overall_strengths=overall_strengths or ["Provided written answers for review."],
        overall_weaknesses=overall_weaknesses or ["Add more specific examples and outcomes."],
        suggested_improvements=suggestions,
        answer_evaluations=answers,
    )


def evaluate_answers(data: EvaluationInput) -> tuple[InterviewEvaluationDraft, str]:
    if getattr(settings, "llm_enabled", False):
        return generate_with_llm(data), "llm"
    return generate_heuristic(data), "heuristic"
