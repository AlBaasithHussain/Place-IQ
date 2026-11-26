"""Job description ORM model: one row per analyzed job description."""

from sqlalchemy import (
    JSON,
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


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    job_title = Column(String(200), nullable=False)
    original_text = Column(Text, nullable=False)

    required_skills = Column(JSON, nullable=False, default=list)
    preferred_skills = Column(JSON, nullable=False, default=list)
    programming_languages = Column(JSON, nullable=False, default=list)
    frameworks = Column(JSON, nullable=False, default=list)
    databases = Column(JSON, nullable=False, default=list)
    cloud_technologies = Column(JSON, nullable=False, default=list)
    tools = Column(JSON, nullable=False, default=list)
    soft_skills = Column(JSON, nullable=False, default=list)
    experience_requirements = Column(JSON, nullable=False, default=list)
    education_requirements = Column(JSON, nullable=False, default=list)

    # "llm" when AI extraction ran, "heuristic" when no API key is configured.
    analysis_engine = Column(String(20), nullable=False, default="heuristic")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="jobs")
