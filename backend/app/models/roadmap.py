"""Roadmap ORM models: one plan with many daily tasks."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id = Column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_id = Column(
        Integer,
        ForeignKey("match_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )

    job_title = Column(String(200), nullable=False)
    match_score = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)
    hours_per_day = Column(Float, nullable=False)
    generation_engine = Column(String(20), nullable=False, default="heuristic")
    priority_skills = Column(JSON, nullable=False, default=list)
    summary = Column(Text, nullable=False, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="roadmaps")
    tasks = relationship(
        "RoadmapTask",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapTask.day",
    )


class RoadmapTask(Base):
    __tablename__ = "roadmap_tasks"

    id = Column(Integer, primary_key=True, index=True)
    roadmap_id = Column(
        Integer,
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    day = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    priority = Column(String(10), nullable=False, default="medium")
    estimated_minutes = Column(Integer, nullable=False)
    learning_topics = Column(JSON, nullable=False, default=list)
    practice_tasks = Column(JSON, nullable=False, default=list)
    mini_project = Column(Text, nullable=False, default="")

    completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    roadmap = relationship("Roadmap", back_populates="tasks")
