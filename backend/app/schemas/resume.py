"""Resume request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ParsedResume(BaseModel):
    name: str | None = None
    email: str | None = None
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)


class ResumeSummary(BaseModel):
    id: int
    original_filename: str
    file_size: int
    created_at: datetime
    name: str | None = None
    email: str | None = None


class ResumeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    original_filename: str
    file_size: int
    mime_type: str
    created_at: datetime
    raw_text: str
    parsed_data: ParsedResume
