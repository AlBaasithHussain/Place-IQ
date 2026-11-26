"""Student profile ORM model (one-to-one with a User)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    college = Column(String(255), nullable=True)
    degree = Column(String(120), nullable=True)
    branch = Column(String(120), nullable=True)
    graduation_year = Column(Integer, nullable=True)
    target_role = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="profile")
