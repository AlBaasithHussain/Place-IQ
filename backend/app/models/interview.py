"""Interview ORM models: one session with many answered questions."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class Interview(Base):
    __tablename__ = "interviews"

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

    job_title = Column(String(200), nullable=False)
    question_count = Column(Integer, nullable=False)
    generation_engine = Column(String(20), nullable=False, default="heuristic")
    status = Column(String(20), nullable=False, default="in_progress")
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="interviews")
    job = relationship("Job")
    resume = relationship("Resume")
    questions = relationship(
        "InterviewQuestion",
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewQuestion.position",
    )
    evaluation = relationship(
        "InterviewEvaluation",
        back_populates="interview",
        cascade="all, delete-orphan",
        uselist=False,
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(
        Integer,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    position = Column(Integer, nullable=False)
    category = Column(String(30), nullable=False)
    question = Column(Text, nullable=False)
    focus_skill = Column(String(200), nullable=False, default="")
    answer = Column(Text, nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)

    interview = relationship("Interview", back_populates="questions")
