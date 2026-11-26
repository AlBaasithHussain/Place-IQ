"""Unit tests for the deterministic scoring algorithm (no AI, no database)."""

from app.schemas.analysis import SkillStatus
from app.services.analysis.scorer import (
    WEIGHTS,
    round_score,
    score_match,
)

JOB = {
    "job_title": "Python Developer",
    "required_skills": ["Python", "SQL", "Docker"],
    "preferred_skills": ["Git"],
    "programming_languages": ["Python", "SQL"],
    "frameworks": [],
    "databases": [],
    "cloud_technologies": [],
    "tools": ["Docker", "Git"],
    "soft_skills": ["Communication"],
    "experience_requirements": [],
    "education_requirements": [],
}


def _minimal_job(**overrides):
    job = {
        "job_title": "Developer",
        "required_skills": [],
        "preferred_skills": [],
        "programming_languages": [],
        "frameworks": [],
        "databases": [],
        "cloud_technologies": [],
        "tools": [],
        "soft_skills": [],
        "experience_requirements": [],
        "education_requirements": [],
    }
    job.update(overrides)
    return job


def _statuses(result):
    return {comparison.skill: comparison.status for comparison in result.comparisons}


def test_example_classification_and_score():
    result = score_match(["Python", "PostgreSQL", "Git"], JOB)
    statuses = _statuses(result)

    assert statuses["Python"] == SkillStatus.MATCH
    assert statuses["SQL"] == SkillStatus.PARTIAL
    assert statuses["Docker"] == SkillStatus.MISSING
    assert statuses["Git"] == SkillStatus.MATCH

    assert "Python" in result.matching_skills
    assert "Git" in result.matching_skills
    assert result.partial_skills == ["SQL"]
    assert "Docker" in result.missing_skills
    assert "Communication" in result.missing_skills
    assert result.bonus_skills == ["Git"]

    # (1 + 0.5 + 0)/3 * 70  +  1*15  +  1*10  +  0*5 = 60
    assert result.score == 60
    assert result.breakdown.required_skills.points == 35
    assert result.breakdown.preferred_skills.points == 15
    assert result.breakdown.projects_experience.points == 10
    assert result.breakdown.soft_skills.points == 0


def test_all_skills_present_scores_100():
    result = score_match(
        ["Python", "Docker", "Communication"],
        _minimal_job(
            required_skills=["Python"],
            preferred_skills=["Docker"],
            soft_skills=["Communication"],
        ),
    )
    assert result.score == 100
    assert result.missing_skills == []
    assert set(result.bonus_skills) == {"Docker"}


def test_empty_requirement_groups_are_neutral():
    result = score_match([], _minimal_job())
    assert result.score == 100
    assert result.comparisons == []


def test_years_ratio_is_capped_and_deterministic():
    result = score_match(
        ["Python"],
        _minimal_job(required_skills=["Python"], experience_requirements=["5+ years of experience"]),
        resume_experience=["2 years of experience"],
    )

    details = result.breakdown.projects_experience.details
    assert details["required_years"] == 5
    assert details["resume_years"] == 2
    assert details["years_credit"] == 0.4
    # 70 + 15 + 5 + (0.7*0.4 + 0.3*1)*10 = 95.8 -> 96
    assert result.score == 96


def test_extra_experience_years_are_capped():
    result = score_match(
        ["Python"],
        _minimal_job(required_skills=["Python"], experience_requirements=["2+ years"]),
        resume_experience=["9 years of experience"],
    )
    assert result.breakdown.projects_experience.details["years_credit"] == 1.0
    assert result.score == 100


def test_keyword_overlap_in_experience_counts():
    result = score_match(
        ["Python"],
        _minimal_job(
            required_skills=["Python"],
            experience_requirements=["3+ years with Django and React"],
        ),
        resume_experience=["4 years building Django apps"],
        resume_projects=["React dashboard"],
    )
    details = result.breakdown.projects_experience.details
    assert details["years_credit"] == 1.0
    assert details["keyword_credit"] == 1.0
    assert result.score == 100


def test_partial_relations_are_symmetric():
    result = score_match(["Next.js"], _minimal_job(required_skills=["React"]))
    assert _statuses(result)["React"] == SkillStatus.PARTIAL
    assert result.score == 65  # 0.5*70 + 1*15 + 1*10 + 1*5 = 65


def test_job_skill_aliases_are_canonicalised():
    result = score_match(["PostgreSQL"], _minimal_job(required_skills=["Postgres"]))
    assert _statuses(result)["PostgreSQL"] == SkillStatus.MATCH
    assert result.score == 100


def test_round_score_is_half_up():
    assert round_score(0.125) == 13
    assert round_score(0.124) == 12


def test_breakdown_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    result = score_match(["Python"], _minimal_job(required_skills=["Python"]))
    parts = result.breakdown.model_dump()
    assert round(sum(part["weight"] for part in parts.values()), 6) == 1.0
    assert all("points" in part and "credit" in part for part in parts.values())
