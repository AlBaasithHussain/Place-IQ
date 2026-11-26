"""Schemas for deterministic resume↔job matching."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SkillStatus(str, Enum):
    MATCH = "match"
    PARTIAL = "partial"
    MISSING = "missing"


class RequirementType(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    SOFT = "soft"


class SkillComparison(BaseModel):
    skill: str
    status: SkillStatus
    requirement_type: RequirementType


class BreakdownPart(BaseModel):
    weight: float
    credit: float
    points: float
    details: dict[str, Any] = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    required_skills: BreakdownPart
    preferred_skills: BreakdownPart
    projects_experience: BreakdownPart
    soft_skills: BreakdownPart


class MatchResult(BaseModel):
    score: int
    matching_skills: list[str]
    partial_skills: list[str]
    missing_skills: list[str]
    bonus_skills: list[str]
    comparisons: list[SkillComparison]
    breakdown: ScoreBreakdown
    explanation: str


class MatchRequest(BaseModel):
    resume_id: int = Field(gt=0)
    job_id: int = Field(gt=0)


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    job_id: int
    score: int
    created_at: datetime


class MatchDetail(MatchResult):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    resume_id: int
    job_id: int
    created_at: datetime
