"""Create database tables from the SQLAlchemy metadata.

Called on app startup and available as a CLI helper:

    python -m app.db.init_db
"""

from app.db.session import Base, engine
from app.models import (  # noqa: F401 - register models
    AnswerEvaluation,
    Interview,
    InterviewEvaluation,
    InterviewQuestion,
    Job,
    MatchAnalysis,
    Resume,
    Roadmap,
    RoadmapTask,
    StudentProfile,
    User,
)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
    print(
        "Tables created (users, student_profiles, resumes, jobs, match_analyses, "
        "roadmaps, roadmap_tasks, interviews, interview_questions, "
        "interview_evaluations, answer_evaluations)."
    )
