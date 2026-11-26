"""Schemas for AI-generated mock interview sessions."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestionCategory(str, Enum):
    TECHNICAL = "technical"
    HR = "hr"
    BEHAVIORAL = "behavioral"
    PROJECT = "project_based"
    PROBLEM = "problem_solving"


class InterviewStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class QuestionDraft(BaseModel):
    category: QuestionCategory
    question: str = Field(min_length=1, max_length=500)
    focus_skill: str = Field(default="", max_length=200)

    @field_validator("question", "focus_skill", mode="before")
    @classmethod
    def _clean_text(cls, value: object) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("expected a string")
        return value.strip()[:500]


class InterviewPlan(BaseModel):
    questions: list[QuestionDraft] = Field(default_factory=list, max_length=10)


class InterviewStartRequest(BaseModel):
    resume_id: int = Field(gt=0)
    job_id: int = Field(gt=0)
    question_count: int = Field(default=5, ge=5, le=10)


class AnswerRequest(BaseModel):
    question_id: int = Field(gt=0)
    answer: str = Field(min_length=1, max_length=10000)

    @field_validator("answer")
    @classmethod
    def _clean_answer(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("answer must not be empty")
        return cleaned


class QuestionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int
    position: int
    category: QuestionCategory
    question: str
    focus_skill: str
    answer: str | None
    answered_at: datetime | None


class InterviewDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    resume_id: int
    job_id: int
    job_title: str
    question_count: int
    generation_engine: str
    status: InterviewStatus
    created_at: datetime
    completed_at: datetime | None
    questions: list[QuestionDetail]
    answered_count: int
    progress_percentage: int
    current_question_number: int | None
    is_complete: bool
    has_evaluation: bool


class InterviewSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    job_id: int
    job_title: str
    question_count: int
    generation_engine: str
    status: InterviewStatus
    created_at: datetime
    progress_percentage: int
    has_evaluation: bool


class AnswerEvaluationDraft(BaseModel):
    position: int = Field(ge=1, le=10)
    score: int = Field(ge=0, le=100)
    technical_accuracy: int = Field(ge=0, le=100)
    relevance: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    strengths: list[str] = Field(min_length=1, max_length=3)
    weaknesses: list[str] = Field(min_length=1, max_length=3)
    suggested_improvement: str = Field(min_length=1, max_length=1000)
    model_answer: str = Field(min_length=1, max_length=4000)

    @field_validator("strengths", "weaknesses", mode="before")
    @classmethod
    def _clean_list(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("expected a list")
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("expected a list of strings")
            text = item.strip()
            if text:
                cleaned.append(text[:400])
        return cleaned

    @field_validator("suggested_improvement", "model_answer", mode="before")
    @classmethod
    def _clean_text(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("expected a string")
        return value.strip()


class InterviewEvaluationDraft(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    overall_summary: str = Field(min_length=1, max_length=2000)
    overall_strengths: list[str] = Field(min_length=1, max_length=3)
    overall_weaknesses: list[str] = Field(min_length=1, max_length=3)
    suggested_improvements: list[str] = Field(min_length=1, max_length=3)
    answer_evaluations: list[AnswerEvaluationDraft] = Field(max_length=10)

    @field_validator("overall_strengths", "overall_weaknesses", "suggested_improvements", mode="before")
    @classmethod
    def _clean_list(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("expected a list")
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("expected a list of strings")
            text = item.strip()
            if text:
                cleaned.append(text[:400])
        return cleaned

    @field_validator("overall_summary", mode="before")
    @classmethod
    def _clean_text(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("expected a string")
        return value.strip()


class AnswerEvaluationDetail(BaseModel):
    id: int
    evaluation_id: int
    question_id: int
    position: int
    category: QuestionCategory
    question: str
    answer: str
    focus_skill: str
    score: int
    technical_accuracy: int
    relevance: int
    completeness: int
    clarity: int
    strengths: list[str]
    weaknesses: list[str]
    suggested_improvement: str
    model_answer: str


class EvaluationResult(BaseModel):
    id: int
    interview_id: int
    job_title: str
    overall_score: int
    generation_engine: str
    overall_summary: str
    overall_strengths: list[str]
    overall_weaknesses: list[str]
    suggested_improvements: list[str]
    question_count: int
    evaluated_answer_count: int
    answer_evaluations: list[AnswerEvaluationDetail]
    created_at: datetime
    updated_at: datetime
