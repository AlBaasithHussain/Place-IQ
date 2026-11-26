from app.schemas.readiness import (
    PlacementReadiness,
    ReadinessComponent,
    TargetSkillAnalysis,
    TargetSkillFrequency,
)

READINESS_WEIGHTS = (
    ("skill_match", "Skill Match", 0.30),
    ("interview_performance", "Interview Performance", 0.25),
    ("technical_preparation", "Technical Preparation", 0.20),
    ("resume_strength", "Resume Strength", 0.15),
    ("learning_progress", "Learning Progress", 0.10),
)

READINESS_FORMULA = (
    "Placement Readiness = Skill Match 30% + Interview Performance 25% + "
    "Technical Preparation 20% + Resume Strength 15% + Learning Progress 10%"
)


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


def _average(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def calculate_readiness(
    *,
    skill_match: int,
    interview_performance: int,
    technical_preparation: int,
    resume_strength: int,
    learning_progress: int,
) -> PlacementReadiness:
    scores = {
        "skill_match": _clamp(skill_match),
        "interview_performance": _clamp(interview_performance),
        "technical_preparation": _clamp(technical_preparation),
        "resume_strength": _clamp(resume_strength),
        "learning_progress": _clamp(learning_progress),
    }
    components = [
        ReadinessComponent(
            key=key,
            label=label,
            weight=weight,
            score=scores[key],
            contribution=round(scores[key] * weight, 1),
        )
        for key, label, weight in READINESS_WEIGHTS
    ]
    score = _clamp(round(sum(item.contribution for item in components)))
    if score >= 80:
        band = "Strong"
    elif score >= 60:
        band = "Job-ready with gaps"
    elif score >= 40:
        band = "Building readiness"
    else:
        band = "Needs foundation"
    return PlacementReadiness(
        score=score,
        band=band,
        formula=READINESS_FORMULA,
        components=components,
    )


def technical_preparation_score(answer_evaluations: list) -> int:
    technical = [
        _clamp(getattr(item, "technical_accuracy", 0))
        for item in answer_evaluations
    ]
    if not technical:
        return 0
    problem_solving = [
        _clamp(getattr(item, "score", 0))
        for item in answer_evaluations
        if getattr(item, "question", None)
        and getattr(item.question, "category", "") == "problem_solving"
    ]
    if problem_solving:
        return _clamp(
            round(
                0.70 * _average(technical)
                + 0.30 * _average(problem_solving)
            )
        )
    return _clamp(round(_average(technical)))


def target_skills_analysis(jobs: list, limit: int = 10) -> TargetSkillAnalysis:
    total_jobs = len(jobs)
    display_names: dict[str, str] = {}
    counts: dict[str, dict] = {}

    for job in jobs:
        per_job: dict[str, set[str]] = {}
        for attribute, requirement_type in (
            ("required_skills", "required"),
            ("preferred_skills", "preferred"),
        ):
            for raw_skill in getattr(job, attribute, None) or []:
                skill = str(raw_skill or "").strip()
                if not skill:
                    continue
                key = skill.casefold()
                display_names.setdefault(key, skill)
                per_job.setdefault(key, set()).add(requirement_type)

        for key, requirement_types in per_job.items():
            entry = counts.setdefault(
                key,
                {
                    "job_count": 0,
                    "required_count": 0,
                    "preferred_count": 0,
                    "requirement_types": set(),
                },
            )
            entry["job_count"] += 1
            if "required" in requirement_types:
                entry["required_count"] += 1
            if "preferred" in requirement_types:
                entry["preferred_count"] += 1
            entry["requirement_types"].update(requirement_types)

    skills: list[TargetSkillFrequency] = []
    for key, entry in counts.items():
        ordered_types = [
            item for item in ("required", "preferred") if item in entry["requirement_types"]
        ]
        skills.append(
            TargetSkillFrequency(
                skill=display_names[key],
                job_count=entry["job_count"],
                total_jobs=total_jobs,
                frequency_percentage=round(entry["job_count"] * 100 / total_jobs)
                if total_jobs
                else 0,
                requirement_types=ordered_types,
                required_count=entry["required_count"],
                preferred_count=entry["preferred_count"],
            )
        )

    skills.sort(key=lambda item: (-item.job_count, item.skill.casefold()))
    return TargetSkillAnalysis(total_jobs=total_jobs, skills=skills[:limit])
