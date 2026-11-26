"""AI-first roadmap generation with a transparent local fallback."""

import json
import re
from dataclasses import dataclass, field

from app.core.config import settings
from app.schemas.roadmap import DayPlan, PriorityLevel, RoadmapPlan
from app.services.jobs.llm import LLMClient, LLMError
from app.services.roadmaps.curriculum import (
    mini_project_for,
    practice_for,
    topics_for,
)

SYSTEM_PROMPT = (
    "You are an expert technical mentor. You build realistic study roadmaps for "
    "students targeting a job. Reply with ONLY a single valid JSON object — no "
    "prose and no markdown. The object MUST have exactly these keys: "
    "priority_skills (array of short strings), summary (short string), days "
    "(array of day objects). Each day object MUST have exactly these keys: day "
    "(integer starting at 1 and increasing by 1 with no gaps), title (short "
    "string), priority (one of \"high\", \"medium\", \"low\"), estimated_minutes "
    "(integer), learning_topics (array of short strings), practice_tasks (array "
    "of short strings), mini_project (short string). Return exactly the requested "
    "number of days. Focus on the missing skills first, then partial skills. "
    "Make every day practical and specific. Never return null."
)

REPAIR_INSTRUCTION = (
    "Your previous reply was not valid JSON for the roadmap schema. Reply again "
    "with ONLY the corrected JSON object, with the exact requested number of "
    "days and no code fences."
)


class RoadmapGenerationError(Exception):
    """Raised when the AI cannot produce a schema-valid roadmap."""


@dataclass
class RoadmapInput:
    job_title: str
    required_skills: list[str]
    missing_skills: list[str]
    partial_skills: list[str]
    resume_skills: list[str]
    match_score: int
    duration_days: int
    hours_per_day: float
    priority_map: dict[str, PriorityLevel] = field(default_factory=dict)


def daily_minutes(data: RoadmapInput) -> int:
    raw = data.hours_per_day * 60
    return max(15, min(480, int(round(raw / 5) * 5)))


def _user_prompt(data: RoadmapInput) -> str:
    return (
        "Create a personalised study roadmap.\n"
        f"Target role: {data.job_title}\n"
        f"Job required skills: {', '.join(data.required_skills) or 'none listed'}\n"
        f"Current resume skills: {', '.join(data.resume_skills) or 'none listed'}\n"
        f"Missing skills to prioritise: {', '.join(data.missing_skills) or 'none listed'}\n"
        f"Partial skills: {', '.join(data.partial_skills) or 'none listed'}\n"
        f"Current match score: {data.match_score}/100\n"
        f"Duration: exactly {data.duration_days} days\n"
        f"Study time available per day: {data.hours_per_day:g} hours "
        f"({daily_minutes(data)} minutes)\n"
        "Each day's estimated_minutes must not exceed the daily budget."
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
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item.strip())
        if len(result) >= limit:
            break
    return result


def _normalise(
    plan: RoadmapPlan,
    data: RoadmapInput,
    budget: int,
) -> RoadmapPlan:
    priority_skills = _dedupe(plan.priority_skills)
    for skill in _dedupe(data.missing_skills) + _dedupe(data.partial_skills):
        if skill not in priority_skills:
            priority_skills.append(skill)
        if len(priority_skills) >= 10:
            break

    days: list[DayPlan] = []
    for index, item in enumerate(plan.days, start=1):
        skill = (
            priority_skills[(index - 1) % len(priority_skills)]
            if priority_skills
            else "general preparation"
        )
        round_index = (index - 1) // max(1, len(priority_skills))
        topics = item.learning_topics or topics_for(skill, round_index)
        practice = item.practice_tasks or practice_for(skill, index)
        project = item.mini_project or mini_project_for(skill, index, data.duration_days)
        title = item.title.strip() or topics[0]
        days.append(
            DayPlan(
                day=index,
                title=title,
                priority=data.priority_map.get(skill, item.priority),
                estimated_minutes=max(10, min(item.estimated_minutes, budget)),
                learning_topics=topics,
                practice_tasks=practice,
                mini_project=project,
            )
        )

    summary = plan.summary.strip() or (
        f"A {data.duration_days}-day plan to close the highest-impact gaps for "
        f"{data.job_title}."
    )
    return RoadmapPlan(priority_skills=priority_skills, summary=summary, days=days)


def _validate(
    content: str,
    data: RoadmapInput,
    budget: int,
) -> RoadmapPlan:
    parsed = json.loads(_strip_code_fences(content))
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON must be an object")
    plan = RoadmapPlan.model_validate(parsed)
    if len(plan.days) != data.duration_days:
        raise ValueError("wrong number of days")
    if [item.day for item in plan.days] != list(range(1, data.duration_days + 1)):
        raise ValueError("days must be sequential")
    return _normalise(plan, data, budget)


def generate_with_llm(data: RoadmapInput) -> RoadmapPlan:
    client = LLMClient(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    budget = daily_minutes(data)
    prompts = [
        _user_prompt(data),
        _user_prompt(data) + "\n\n" + REPAIR_INSTRUCTION,
    ]
    try:
        for prompt in prompts:
            try:
                content = client.complete_json(SYSTEM_PROMPT, prompt)
            except LLMError as exc:
                raise RoadmapGenerationError(
                    "The AI service is unavailable right now. Please try again."
                ) from exc
            try:
                return _validate(content, data, budget)
            except ValueError:
                continue
    except RoadmapGenerationError:
        raise
    raise RoadmapGenerationError(
        "The AI returned data that failed roadmap validation."
    )


def generate_heuristic(data: RoadmapInput) -> RoadmapPlan:
    budget = daily_minutes(data)
    priority_skills = _dedupe(data.missing_skills) + _dedupe(data.partial_skills)
    priority_skills = _dedupe(priority_skills)
    if not priority_skills:
        priority_skills = ["general preparation"]

    days: list[DayPlan] = []
    for index in range(1, data.duration_days + 1):
        skill = priority_skills[(index - 1) % len(priority_skills)]
        round_index = (index - 1) // len(priority_skills)
        topics = topics_for(skill, round_index)
        title = (
            "Mini Project & Practice Interview"
            if index == data.duration_days
            else topics[0]
        )
        priority = data.priority_map.get(skill, PriorityLevel.MEDIUM)
        days.append(
            DayPlan(
                day=index,
                title=title,
                priority=priority,
                estimated_minutes=budget,
                learning_topics=topics,
                practice_tasks=practice_for(skill, index),
                mini_project=mini_project_for(skill, index, data.duration_days),
            )
        )

    return RoadmapPlan(
        priority_skills=priority_skills[:10],
        summary=(
            f"A {data.duration_days}-day roadmap built from the highest-impact "
            f"gaps for {data.job_title}."
        ),
        days=days,
    )


def generate_roadmap(data: RoadmapInput) -> tuple[RoadmapPlan, str]:
    if getattr(settings, "llm_enabled", False):
        return generate_with_llm(data), "llm"
    return generate_heuristic(data), "heuristic"
