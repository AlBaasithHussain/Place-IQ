"""AI-first mock interview question generation with a local fallback."""

import json
import re
from dataclasses import dataclass

from app.core.config import settings
from app.schemas.interview import InterviewPlan, QuestionCategory, QuestionDraft
from app.services.jobs.llm import LLMClient, LLMError

SYSTEM_PROMPT = (
    "You are a senior technical interviewer. Generate realistic mock interview "
    "questions tailored to the candidate and role. Reply with ONLY a single valid "
    "JSON object — no prose and no markdown. The object MUST have exactly one key: "
    "questions (array). Each question object MUST have exactly these keys: "
    "category (one of \"technical\", \"hr\", \"behavioral\", \"project_based\", "
    "\"problem_solving\"), question (string), focus_skill (string). Include at "
    "least one question from every category. Ask about the candidate's real "
    "skills and projects, and probe missing skills without being hostile. "
    "Never return null."
)

REPAIR_INSTRUCTION = (
    "Your previous reply was not valid JSON for the interview schema. Reply again "
    "with ONLY the corrected JSON object, the exact requested number of questions, "
    "all five categories, and no code fences."
)

_CATEGORY_ORDER = (
    QuestionCategory.TECHNICAL,
    QuestionCategory.PROJECT,
    QuestionCategory.BEHAVIORAL,
    QuestionCategory.PROBLEM,
    QuestionCategory.HR,
)


class InterviewGenerationError(Exception):
    """Raised when the AI cannot produce schema-valid interview questions."""


@dataclass
class InterviewInput:
    job_title: str
    job_description: str
    required_skills: list[str]
    resume_skills: list[str]
    projects: list[str]
    missing_skills: list[str]
    match_score: int
    question_count: int


def _user_prompt(data: InterviewInput) -> str:
    description = data.job_description[:4000]
    return (
        "Generate a mock interview question set.\n"
        f"Target role: {data.job_title}\n"
        f"Job description:\n{description}\n"
        f"Job required skills: {', '.join(data.required_skills) or 'none listed'}\n"
        f"Candidate skills: {', '.join(data.resume_skills) or 'none listed'}\n"
        f"Candidate projects: {'; '.join(data.projects) or 'none listed'}\n"
        f"Missing skills: {', '.join(data.missing_skills) or 'none listed'}\n"
        f"Current match score: {data.match_score}/100\n"
        f"Return exactly {data.question_count} questions."
    )


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


def _dedupe(items: list[str], limit: int = 10) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        key = cleaned.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def _focus_pool(data: InterviewInput) -> list[str]:
    pool = _dedupe(data.missing_skills + data.required_skills + data.resume_skills)
    return pool or [data.job_title]


def _short(text: str, limit: int = 140) -> str:
    cleaned = " ".join(text.split())
    return cleaned[:limit]


def _fallback_question(
    category: QuestionCategory,
    focus: str,
    data: InterviewInput,
    index: int,
) -> str:
    variant = (index // len(_CATEGORY_ORDER)) % 3
    project = (
        _short(data.projects[index % len(data.projects)])
        if data.projects
        else "a project you built"
    )

    if category == QuestionCategory.TECHNICAL:
        templates = (
            f"Explain {focus} and describe how you have used it in practice.",
            f"What trade-offs would you consider when choosing {focus} for this {data.job_title} role?",
            f"A requirement mentions {focus}. How would you design a solution around it?",
        )
    elif category == QuestionCategory.PROJECT:
        templates = (
            f"You mentioned a project involving {project}. Why did you choose that approach?",
            f"Walk me through your contribution to {project} and the result you achieved.",
            f"If you rebuilt {project} today, what would you change and why?",
        )
    elif category == QuestionCategory.BEHAVIORAL:
        templates = (
            "Tell me about a time you disagreed with a teammate. How did you handle it?",
            "Describe a deadline you missed or a mistake you made. What did you learn?",
            "Tell me about a time you had to explain a technical decision to a non-technical audience.",
        )
    elif category == QuestionCategory.PROBLEM:
        templates = (
            f"A feature using {focus} is slow in production. How would you diagnose and fix it?",
            f"Requirements for {focus} change midway through a sprint. How would you adapt the plan?",
            f"How would you break down an ambiguous problem involving {focus}?",
        )
    else:
        templates = (
            f"Why are you interested in this {data.job_title} role?",
            "Where do you see yourself growing over the next year?",
            "What strengths would you bring to our team, and what are you improving?",
        )
    return templates[variant]


def generate_heuristic(data: InterviewInput) -> InterviewPlan:
    pool = _focus_pool(data)
    questions: list[QuestionDraft] = []
    for index in range(data.question_count):
        category = _CATEGORY_ORDER[index % len(_CATEGORY_ORDER)]
        focus = pool[index % len(pool)]
        questions.append(
            QuestionDraft(
                category=category,
                question=_fallback_question(category, focus, data, index),
                focus_skill=focus,
            )
        )
    return InterviewPlan(questions=questions)


def _normalise(plan: InterviewPlan, data: InterviewInput) -> InterviewPlan:
    pool = _focus_pool(data)
    questions: list[QuestionDraft] = []
    for index, item in enumerate(plan.questions):
        questions.append(
            QuestionDraft(
                category=item.category,
                question=item.question,
                focus_skill=item.focus_skill.strip() or pool[index % len(pool)],
            )
        )
    return InterviewPlan(questions=questions)


def _validate(content: str, data: InterviewInput) -> InterviewPlan:
    parsed = json.loads(_strip_code_fences(content))
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON must be an object")
    plan = InterviewPlan.model_validate(parsed)
    if len(plan.questions) != data.question_count:
        raise ValueError("wrong number of questions")
    if len({item.category for item in plan.questions}) < len(_CATEGORY_ORDER):
        raise ValueError("all five categories are required")
    questions = [item.question.strip().lower() for item in plan.questions]
    if len(set(questions)) != len(questions):
        raise ValueError("questions must be unique")
    return _normalise(plan, data)


def generate_with_llm(data: InterviewInput) -> InterviewPlan:
    client = LLMClient(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    prompts = [_user_prompt(data), _user_prompt(data) + "\n\n" + REPAIR_INSTRUCTION]
    try:
        for prompt in prompts:
            try:
                content = client.complete_json(SYSTEM_PROMPT, prompt)
            except LLMError as exc:
                raise InterviewGenerationError(
                    "The AI service is unavailable right now. Please try again."
                ) from exc
            try:
                return _validate(content, data)
            except ValueError:
                continue
    except InterviewGenerationError:
        raise
    raise InterviewGenerationError(
        "The AI returned questions that failed validation."
    )


def generate_questions(data: InterviewInput) -> tuple[InterviewPlan, str]:
    if getattr(settings, "llm_enabled", False):
        return generate_with_llm(data), "llm"
    return generate_heuristic(data), "heuristic"
