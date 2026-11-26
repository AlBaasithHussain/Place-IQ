"""User ORM model."""

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    profile = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    resumes = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    jobs = relationship(
        "Job",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    analyses = relationship(
        "MatchAnalysis",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    roadmaps = relationship(
        "Roadmap",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    interviews = relationship(
        "Interview",
        back_populates="user",
        cascade="all, delete-orphan",
    )
