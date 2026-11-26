from types import SimpleNamespace

from app.services.readiness import (
    calculate_readiness,
    target_skills_analysis,
    technical_preparation_score,
)


def test_calculate_readiness_uses_documented_weights():
    result = calculate_readiness(
        skill_match=90,
        interview_performance=80,
        technical_preparation=70,
        resume_strength=60,
        learning_progress=50,
    )

    assert result.score == 75
    assert result.band == "Job-ready with gaps"
    assert [item.key for item in result.components] == [
        "skill_match",
        "interview_performance",
        "technical_preparation",
        "resume_strength",
        "learning_progress",
    ]
    assert [item.weight for item in result.components] == [0.3, 0.25, 0.2, 0.15, 0.1]
    assert [item.contribution for item in result.components] == [27, 20, 14, 9, 5]
    assert "Skill Match 30%" in result.formula
    assert "Learning Progress 10%" in result.formula


def test_calculate_readiness_clamps_scores_and_bands():
    result = calculate_readiness(
        skill_match=120,
        interview_performance=-20,
        technical_preparation=100,
        resume_strength=50,
        learning_progress=0,
    )

    assert [item.score for item in result.components] == [100, 0, 100, 50, 0]
    assert result.score == 58
    assert result.band == "Building readiness"


def test_technical_preparation_score_uses_accuracy_and_problem_solving():
    evaluations = [
        SimpleNamespace(
            technical_accuracy=80,
            score=70,
            question=SimpleNamespace(category="technical"),
        ),
        SimpleNamespace(
            technical_accuracy=60,
            score=90,
            question=SimpleNamespace(category="problem_solving"),
        ),
    ]

    assert technical_preparation_score(evaluations) == 76
    assert technical_preparation_score([]) == 0


def test_target_skills_analysis_counts_jobs_and_requirement_types():
    jobs = [
        SimpleNamespace(
            required_skills=["Python", "SQL"],
            preferred_skills=["Docker"],
        ),
        SimpleNamespace(
            required_skills=["python", "AWS"],
            preferred_skills=["SQL", "Docker"],
        ),
        SimpleNamespace(
            required_skills=["SQL"],
            preferred_skills=["Git"],
        ),
    ]

    result = target_skills_analysis(jobs)
    assert result.total_jobs == 3
    assert [item.skill for item in result.skills[:3]] == ["SQL", "Docker", "Python"]

    sql = next(item for item in result.skills if item.skill == "SQL")
    assert sql.job_count == 3
    assert sql.frequency_percentage == 100
    assert sql.requirement_types == ["required", "preferred"]
    assert sql.required_count == 2
    assert sql.preferred_count == 1

    python = next(item for item in result.skills if item.skill == "Python")
    assert python.job_count == 2
    assert python.frequency_percentage == 67
    assert python.requirement_types == ["required"]

    limited = target_skills_analysis(jobs, limit=2)
    assert [item.skill for item in limited.skills] == ["SQL", "Docker"]
