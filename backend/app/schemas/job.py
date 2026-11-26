"""Job description request/response schemas.

``JobAnalysisResult`` is both the API response shape and the strict contract we
force the AI to satisfy — the LLM output must validate against it before it is
ever persisted.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_LIST_FIELDS = [
    "required_skills",
    "preferred_skills",
    "programming_languages",
    "frameworks",
    "databases",
    "cloud_technologies",
    "tools",
    "soft_skills",
    "experience_requirements",
    "education_requirements",
]

MAX_ITEMS = 50
MAX_ITEM_LENGTH = 200


class JobAnalysisResult(BaseModel):
    job_title: str = Field(min_length=1, max_length=200)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud_technologies: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)

    @field_validator("job_title")
    @classmethod
    def _clean_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("job_title must not be empty")
        return cleaned

    @field_validator(*_LIST_FIELDS, mode="before")
    @classmethod
    def _clean_list(cls, value: object) -> list[str]:
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
            cleaned.append(text[:MAX_ITEM_LENGTH])
            if len(cleaned) >= MAX_ITEMS:
                break
        return cleaned


class JobAnalyzeRequest(BaseModel):
    text: str = Field(max_length=20000)

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 30:
            raise ValueError("Job description must be at least 30 characters")
        return cleaned


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_title: str
    analysis_engine: str
    created_at: datetime


class JobDetail(JobAnalysisResult):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    original_text: str
    analysis_engine: str
    created_at: datetime
    updated_at: datetime
