from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.readiness import PlacementReadiness, TargetSkillAnalysis


class DashboardOverview(BaseModel):
    resume_score: int
    resume_file_name: str | None = None
    job_match_score: int
    interview_score: int
    skills_learned: int
    learned_skills: list[str] = Field(default_factory=list)
    latest_analysis_id: int | None = None
    latest_interview_id: int | None = None


class DashboardSkill(BaseModel):
    skill: str
    requirement_type: str | None = None


class DashboardSkillAnalysis(BaseModel):
    analysis_id: int | None = None
    job_title: str | None = None
    strong_skills: list[DashboardSkill] = Field(default_factory=list)
    partial_skills: list[DashboardSkill] = Field(default_factory=list)
    missing_skills: list[DashboardSkill] = Field(default_factory=list)


class DashboardLearningProgress(BaseModel):
    has_roadmap: bool
    roadmap_id: int | None = None
    job_title: str | None = None
    duration_days: int
    total_tasks: int
    completed_tasks: int
    remaining_tasks: int
    progress_percentage: int
    priority_skills: list[str] = Field(default_factory=list)
    summary: str = ""


class DashboardInterviewStats(BaseModel):
    sessions: int
    completed_sessions: int
    questions_attempted: int
    questions_total: int
    evaluated_sessions: int
    average_score: int
    latest_score: int


class RecentJob(BaseModel):
    id: int
    job_title: str
    analysis_engine: str
    created_at: datetime
    match_score: int | None = None


class ScoreTrendPoint(BaseModel):
    label: str
    value: int


class DashboardTrends(BaseModel):
    match_scores: list[ScoreTrendPoint] = Field(default_factory=list)
    interview_scores: list[ScoreTrendPoint] = Field(default_factory=list)


class DashboardData(BaseModel):
    has_data: bool
    overview: DashboardOverview
    readiness: PlacementReadiness
    skill_analysis: DashboardSkillAnalysis
    learning_progress: DashboardLearningProgress
    interview: DashboardInterviewStats
    recent_jobs: list[RecentJob] = Field(default_factory=list)
    target_skills: TargetSkillAnalysis
    trends: DashboardTrends
