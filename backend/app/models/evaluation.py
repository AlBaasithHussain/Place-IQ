from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    JSON,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class InterviewEvaluation(Base):
    __tablename__ = "interview_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(
        Integer,
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    overall_score = Column(Integer, nullable=False)
    generation_engine = Column(String(20), nullable=False, default="heuristic")
    overall_summary = Column(Text, nullable=False)
    overall_strengths = Column(JSON, nullable=False)
    overall_weaknesses = Column(JSON, nullable=False)
    suggested_improvements = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    interview = relationship("Interview", back_populates="evaluation")
    answer_evaluations = relationship(
        "AnswerEvaluation",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="AnswerEvaluation.position",
    )


class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"
    __table_args__ = (UniqueConstraint("evaluation_id", "position", name="uq_answer_evaluation_position"),)

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(
        Integer,
        ForeignKey("interview_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)
    technical_accuracy = Column(Integer, nullable=False)
    relevance = Column(Integer, nullable=False)
    completeness = Column(Integer, nullable=False)
    clarity = Column(Integer, nullable=False)
    strengths = Column(JSON, nullable=False)
    weaknesses = Column(JSON, nullable=False)
    suggested_improvement = Column(Text, nullable=False)
    model_answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluation = relationship("InterviewEvaluation", back_populates="answer_evaluations")
    question = relationship("InterviewQuestion")
