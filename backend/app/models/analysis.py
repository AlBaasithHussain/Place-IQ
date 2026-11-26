"""Match-analysis ORM model: one row per deterministic resume↔job comparison."""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class MatchAnalysis(Base):
    __tablename__ = "match_analyses"

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
        index=True,
    )
    job_id = Column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score = Column(Integer, nullable=False)
    result = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="analyses")
