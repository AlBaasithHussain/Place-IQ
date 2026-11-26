from pydantic import BaseModel, Field


class ReadinessComponent(BaseModel):
    key: str
    label: str
    weight: float = Field(ge=0, le=1)
    score: int
    contribution: float


class PlacementReadiness(BaseModel):
    score: int
    band: str
    formula: str
    components: list[ReadinessComponent]


class TargetSkillFrequency(BaseModel):
    skill: str
    job_count: int
    total_jobs: int
    frequency_percentage: int
    requirement_types: list[str]
    required_count: int
    preferred_count: int


class TargetSkillAnalysis(BaseModel):
    total_jobs: int
    skills: list[TargetSkillFrequency]
