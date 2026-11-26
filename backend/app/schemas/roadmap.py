"""Schemas for AI-generated, backend-validated study roadmaps."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PriorityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_MAX_ITEMS = 5
_MAX_TEXT = 300


def _clean_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        raise ValueError("expected a list of strings")
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError("list items must be strings")
        text = item.strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text[:_MAX_TEXT])
        if len(cleaned) >= _MAX_ITEMS:
            break
    return cleaned


class DayPlan(BaseModel):
    day: int = Field(ge=1, le=14)
    title: str = Field(min_length=1, max_length=200)
    priority: PriorityLevel = PriorityLevel.MEDIUM
    estimated_minutes: int = Field(ge=10, le=10080)
    learning_topics: list[str] = Field(default_factory=list)
    practice_tasks: list[str] = Field(default_factory=list)
    mini_project: str = Field(default="", max_length=_MAX_TEXT)

    @field_validator("title", "mini_project", mode="before")
    @classmethod
    def _clean_text(cls, value: object) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("expected a string")
        return value.strip()[:_MAX_TEXT]

    @field_validator("learning_topics", "practice_tasks", mode="before")
    @classmethod
    def _clean_lists(cls, value: object) -> list[str]:
        return _clean_list(value)


class RoadmapPlan(BaseModel):
    priority_skills: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=1000)
    days: list[DayPlan] = Field(default_factory=list, max_length=14)

    @field_validator("priority_skills", mode="before")
    @classmethod
    def _clean_priority_skills(cls, value: object) -> list[str]:
        return _clean_list(value)

    @field_validator("summary", mode="before")
    @classmethod
    def _clean_summary(cls, value: object) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("expected a string")
        return value.strip()[:1000]


class RoadmapGenerateRequest(BaseModel):
    analysis_id: int = Field(gt=0)
    duration_days: Literal[7, 14] = 7
    hours_per_day: float = Field(default=1.0, ge=0.25, le=8.0)


class RoadmapTaskUpdate(BaseModel):
    completed: bool


class RoadmapTaskDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    roadmap_id: int
    day: int
    title: str
    priority: PriorityLevel
    estimated_minutes: int
    learning_topics: list[str]
    practice_tasks: list[str]
    mini_project: str
    completed: bool
    completed_at: datetime | None


class RoadmapDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    resume_id: int
    job_id: int
    analysis_id: int
    job_title: str
    match_score: int
    duration_days: int
    hours_per_day: float
    generation_engine: str
    priority_skills: list[str]
    summary: str
    created_at: datetime
    tasks: list[RoadmapTaskDetail]
    total_estimated_minutes: int
    completed_count: int
    progress_percentage: int


class RoadmapSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_id: int
    job_title: str
    match_score: int
    duration_days: int
    generation_engine: str
    created_at: datetime
    progress_percentage: int
