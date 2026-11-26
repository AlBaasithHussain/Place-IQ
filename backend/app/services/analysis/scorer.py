"""Deterministic match scoring. No LLM is involved in this calculation."""

import math
import re
from collections.abc import Iterable

from app.schemas.analysis import (
    BreakdownPart,
    MatchResult,
    RequirementType,
    ScoreBreakdown,
    SkillComparison,
    SkillStatus,
)
from app.schemas.job import JobAnalysisResult
from app.services.analysis.relations import canonicalize, classify

WEIGHTS = {
    "required_skills": 0.70,
    "preferred_skills": 0.15,
    "projects_experience": 0.10,
    "soft_skills": 0.05,
}

STATUS_CREDIT = {
    SkillStatus.MATCH: 1.0,
    SkillStatus.PARTIAL: 0.5,
    SkillStatus.MISSING: 0.0,
}

SCORE_FORMULA = (
    "Score = 70% required skills + 15% preferred skills + 10% projects/experience "
    "+ 5% soft skills. For each skill group: MATCH = 1.0, PARTIAL = 0.5, "
    "MISSING = 0.0, averaged over the skills listed in that group; an empty "
    "group scores 1.0 so it does not penalise the student. Projects/experience "
    "= 70% years ratio (resume years / required years, capped at 1.0; 1.0 when "
    "the job states no years) + 30% share of job experience lines sharing a "
    "meaningful keyword with the resume's experience/projects text (lines with "
    "no meaningful keywords count as neutral matches; 1.0 when there are no "
    "job experience lines). The weighted total is multiplied by 100 and rounded "
    "half-up. PARTIAL means a curated close relative is on the resume, e.g. "
    "PostgreSQL counts as PARTIAL for SQL."
)

_STOPWORDS = {
    "ability",
    "and",
    "an",
    "are",
    "build",
    "building",
    "development",
    "experience",
    "for",
    "from",
    "have",
    "in",
    "knowledge",
    "minimum",
    "more",
    "of",
    "or",
    "our",
    "plus",
    "preferred",
    "required",
    "skills",
    "strong",
    "team",
    "than",
    "the",
    "using",
    "will",
    "with",
    "work",
    "working",
    "year",
    "years",
    "your",
}
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]{2,}")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def round_score(raw: float) -> int:
    """Convert a 0..1 weighted credit into an integer percent, half-up."""
    return int(math.floor(raw * 100 + 0.5))


def _tokens(text: str) -> set[str]:
    return {
        token.lower().strip(".-")
        for token in _TOKEN_RE.findall(text)
        if token.lower().strip(".-") not in _STOPWORDS
    }


def _years(lines: Iterable[str], *, use_min: bool) -> float | None:
    values: list[float] = []
    for line in lines:
        if "year" not in line.casefold():
            continue
        match = _NUMBER_RE.search(line)
        if match:
            values.append(float(match.group(0)))
    if not values:
        return None
    return min(values) if use_min else max(values)


def _experience_credit(
    job_lines: list[str],
    resume_experience: list[str],
    resume_projects: list[str],
) -> tuple[float, dict]:
    job_lines = [line.strip() for line in job_lines if line.strip()]
    required_years = _years(job_lines, use_min=True)
    resume_years = _years(resume_experience, use_min=False)

    if required_years and required_years > 0:
        years_credit = min((resume_years or 0.0) / required_years, 1.0)
    else:
        years_credit = 1.0

    resume_tokens = _tokens(" ".join([*resume_experience, *resume_projects]))
    matched = 0
    for line in job_lines:
        tokens = _tokens(line)
        if not tokens or tokens & resume_tokens:
            matched += 1
    keyword_credit = matched / len(job_lines) if job_lines else 1.0

    credit = 0.70 * years_credit + 0.30 * keyword_credit
    details = {
        "required_years": required_years,
        "resume_years": resume_years,
        "years_credit": round(years_credit, 4),
        "keyword_credit": round(keyword_credit, 4),
    }
    return credit, details


def _group_credit(
    skills: list[str],
    resume_skills: set[str],
    requirement_type: RequirementType,
    comparisons: list[SkillComparison],
) -> tuple[float, dict]:
    statuses = []
    for skill in skills:
        status = classify(skill, resume_skills)
        comparisons.append(
            SkillComparison(
                skill=canonicalize(skill),
                status=status,
                requirement_type=requirement_type,
            )
        )
        statuses.append(status)

    credit = (
        sum(STATUS_CREDIT[status] for status in statuses) / len(statuses)
        if statuses
        else 1.0
    )
    details = {
        "match_count": sum(s == SkillStatus.MATCH for s in statuses),
        "partial_count": sum(s == SkillStatus.PARTIAL for s in statuses),
        "missing_count": sum(s == SkillStatus.MISSING for s in statuses),
    }
    return credit, details


def _part(weight: float, credit: float, details: dict) -> BreakdownPart:
    return BreakdownPart(
        weight=weight,
        credit=round(credit, 4),
        points=round(weight * credit * 100, 2),
        details=details,
    )


def score_match(
    resume_skills: Iterable[str],
    job_data: dict,
    resume_experience: Iterable[str] = (),
    resume_projects: Iterable[str] = (),
) -> MatchResult:
    """Compute a full, deterministic comparison result from plain data."""
    job = JobAnalysisResult.model_validate(job_data)
    skills = {canonicalize(skill) for skill in resume_skills}
    comparisons: list[SkillComparison] = []

    required_credit, required_details = _group_credit(
        job.required_skills, skills, RequirementType.REQUIRED, comparisons
    )
    preferred_credit, preferred_details = _group_credit(
        job.preferred_skills, skills, RequirementType.PREFERRED, comparisons
    )
    soft_credit, soft_details = _group_credit(
        job.soft_skills, skills, RequirementType.SOFT, comparisons
    )
    experience_credit, experience_details = _experience_credit(
        job.experience_requirements,
        list(resume_experience),
        list(resume_projects),
    )

    raw = (
        WEIGHTS["required_skills"] * required_credit
        + WEIGHTS["preferred_skills"] * preferred_credit
        + WEIGHTS["projects_experience"] * experience_credit
        + WEIGHTS["soft_skills"] * soft_credit
    )

    matching = list(dict.fromkeys(c.skill for c in comparisons if c.status == SkillStatus.MATCH))
    partial = list(dict.fromkeys(c.skill for c in comparisons if c.status == SkillStatus.PARTIAL))
    missing = list(dict.fromkeys(c.skill for c in comparisons if c.status == SkillStatus.MISSING))
    bonus = list(
        dict.fromkeys(
            c.skill
            for c in comparisons
            if c.requirement_type == RequirementType.PREFERRED
            and c.status in (SkillStatus.MATCH, SkillStatus.PARTIAL)
        )
    )

    breakdown = ScoreBreakdown(
        required_skills=_part(WEIGHTS["required_skills"], required_credit, required_details),
        preferred_skills=_part(WEIGHTS["preferred_skills"], preferred_credit, preferred_details),
        projects_experience=_part(
            WEIGHTS["projects_experience"], experience_credit, experience_details
        ),
        soft_skills=_part(WEIGHTS["soft_skills"], soft_credit, soft_details),
    )

    return MatchResult(
        score=round_score(raw),
        matching_skills=matching,
        partial_skills=partial,
        missing_skills=missing,
        bonus_skills=bonus,
        comparisons=comparisons,
        breakdown=breakdown,
        explanation=SCORE_FORMULA,
    )
