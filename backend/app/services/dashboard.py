from sqlalchemy.orm import Session

from app.models.analysis import MatchAnalysis
from app.models.evaluation import AnswerEvaluation, InterviewEvaluation
from app.models.interview import Interview
from app.models.job import Job
from app.models.resume import Resume
from app.models.roadmap import Roadmap
from app.schemas.dashboard import (
    DashboardData,
    DashboardInterviewStats,
    DashboardLearningProgress,
    DashboardOverview,
    DashboardSkill,
    DashboardSkillAnalysis,
    DashboardTrends,
    RecentJob,
    ScoreTrendPoint,
)
from app.services.readiness import (
    calculate_readiness,
    target_skills_analysis,
    technical_preparation_score,
)

RESUME_SECTION_WEIGHTS = {
    "name": 6,
    "email": 6,
    "education": 12,
    "skills": 14,
    "programming_languages": 10,
    "frameworks": 8,
    "databases": 8,
    "tools": 8,
    "projects": 14,
    "certifications": 6,
    "experience": 8,
}

RESUME_HEADING_HINTS = {
    "education": ("education", "university", "college"),
    "skills": ("skills", "technical skills"),
    "programming_languages": ("languages", "programming languages"),
    "frameworks": ("frameworks",),
    "databases": ("databases",),
    "tools": ("tools",),
    "projects": ("projects", "project"),
    "certifications": ("certifications", "certificates"),
    "experience": ("experience", "employment", "internship"),
}


def _as_list(value: object) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _present(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_present(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_present(item) for item in value)
    return value is not None


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def _resume_score(parsed_data: dict, raw_text: str) -> int:
    parsed = parsed_data if isinstance(parsed_data, dict) else {}
    text = (raw_text or "").lower()
    score = 0
    for key, weight in RESUME_SECTION_WEIGHTS.items():
        present = _present(parsed.get(key))
        if not present:
            present = any(hint in text for hint in RESUME_HEADING_HINTS.get(key, ()))
        if present:
            score += weight
    return max(0, min(100, score))


def _skill_items(result: dict, key: str) -> list[DashboardSkill]:
    data = result if isinstance(result, dict) else {}
    requirement_by_skill: dict[str, str] = {}
    for comparison in _as_list(data.get("comparisons")):
        if not isinstance(comparison, dict):
            continue
        skill_key = _clean_text(comparison.get("skill")).lower()
        requirement = _clean_text(comparison.get("requirement_type")).lower()
        if skill_key and requirement:
            requirement_by_skill[skill_key] = requirement

    items: list[DashboardSkill] = []
    for skill in _unique([_clean_text(item) for item in _as_list(data.get(key))]):
        items.append(
            DashboardSkill(
                skill=skill,
                requirement_type=requirement_by_skill.get(skill.lower()),
            )
        )
    return items


def _trend_points(rows: list, value_field: str) -> list[ScoreTrendPoint]:
    points: list[ScoreTrendPoint] = []
    for row in rows:
        created_at = getattr(row, "created_at", None)
        label = created_at.strftime("%d %b") if created_at else ""
        points.append(ScoreTrendPoint(label=label, value=int(getattr(row, value_field))))
    return points


def build_dashboard(db: Session, user_id: int) -> DashboardData:
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc(), Resume.id.desc())
        .all()
    )
    jobs = (
        db.query(Job)
        .filter(Job.user_id == user_id)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .all()
    )
    analyses = (
        db.query(MatchAnalysis)
        .filter(MatchAnalysis.user_id == user_id)
        .order_by(MatchAnalysis.created_at.desc(), MatchAnalysis.id.desc())
        .all()
    )
    roadmaps = (
        db.query(Roadmap)
        .filter(Roadmap.user_id == user_id)
        .order_by(Roadmap.created_at.desc(), Roadmap.id.desc())
        .all()
    )
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == user_id)
        .order_by(Interview.created_at.desc(), Interview.id.desc())
        .all()
    )
    evaluations = (
        db.query(InterviewEvaluation)
        .join(Interview)
        .filter(Interview.user_id == user_id)
        .order_by(InterviewEvaluation.created_at.desc(), InterviewEvaluation.id.desc())
        .all()
    )
    answer_evaluations = (
        db.query(AnswerEvaluation)
        .join(InterviewEvaluation, AnswerEvaluation.evaluation_id == InterviewEvaluation.id)
        .join(Interview, InterviewEvaluation.interview_id == Interview.id)
        .filter(Interview.user_id == user_id)
        .all()
    )

    latest_resume = resumes[0] if resumes else None
    latest_analysis = analyses[0] if analyses else None
    latest_evaluation = evaluations[0] if evaluations else None
    seven_day_roadmap = next((item for item in roadmaps if item.duration_days == 7), None)

    learned_skills: list[str] = []
    for roadmap in roadmaps:
        for task in roadmap.tasks:
            if task.completed:
                learned_skills.extend(_clean_text(item) for item in _as_list(task.learning_topics))
    learned_skills = _unique(learned_skills)

    resume_score = (
        _resume_score(latest_resume.parsed_data or {}, latest_resume.raw_text or "")
        if latest_resume
        else 0
    )
    overview = DashboardOverview(
        resume_score=resume_score,
        resume_file_name=latest_resume.original_filename if latest_resume else None,
        job_match_score=int(latest_analysis.score) if latest_analysis else 0,
        interview_score=int(latest_evaluation.overall_score) if latest_evaluation else 0,
        skills_learned=len(learned_skills),
        learned_skills=learned_skills,
        latest_analysis_id=latest_analysis.id if latest_analysis else None,
        latest_interview_id=latest_evaluation.interview_id if latest_evaluation else None,
    )

    analysis_result = latest_analysis.result if latest_analysis and latest_analysis.result else {}
    analysis_job = None
    if latest_analysis:
        analysis_job = next((item for item in jobs if item.id == latest_analysis.job_id), None)
    skill_analysis = DashboardSkillAnalysis(
        analysis_id=latest_analysis.id if latest_analysis else None,
        job_title=analysis_job.job_title if analysis_job else None,
        strong_skills=_skill_items(analysis_result, "matching_skills"),
        partial_skills=_skill_items(analysis_result, "partial_skills"),
        missing_skills=_skill_items(analysis_result, "missing_skills"),
    )

    roadmap_tasks = list(seven_day_roadmap.tasks) if seven_day_roadmap else []
    completed_tasks = sum(1 for task in roadmap_tasks if task.completed)
    total_tasks = len(roadmap_tasks)
    progress = int(round(completed_tasks * 100 / total_tasks)) if total_tasks else 0
    learning_progress = DashboardLearningProgress(
        has_roadmap=seven_day_roadmap is not None,
        roadmap_id=seven_day_roadmap.id if seven_day_roadmap else None,
        job_title=seven_day_roadmap.job_title if seven_day_roadmap else None,
        duration_days=seven_day_roadmap.duration_days if seven_day_roadmap else 0,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        remaining_tasks=total_tasks - completed_tasks,
        progress_percentage=progress,
        priority_skills=_unique(
            [_clean_text(item) for item in _as_list(seven_day_roadmap.priority_skills)]
        )
        if seven_day_roadmap
        else [],
        summary=seven_day_roadmap.summary if seven_day_roadmap else "",
    )

    questions_total = sum(len(item.questions) for item in interviews)
    questions_attempted = sum(
        1 for item in interviews for question in item.questions if question.answer
    )
    evaluated_scores = [int(item.overall_score) for item in evaluations]
    interview_stats = DashboardInterviewStats(
        sessions=len(interviews),
        completed_sessions=sum(1 for item in interviews if item.status == "completed"),
        questions_attempted=questions_attempted,
        questions_total=questions_total,
        evaluated_sessions=len(evaluated_scores),
        average_score=int(round(sum(evaluated_scores) / len(evaluated_scores)))
        if evaluated_scores
        else 0,
        latest_score=evaluated_scores[0] if evaluated_scores else 0,
    )

    readiness = calculate_readiness(
        skill_match=overview.job_match_score,
        interview_performance=interview_stats.average_score,
        technical_preparation=technical_preparation_score(answer_evaluations),
        resume_strength=resume_score,
        learning_progress=progress,
    )
    target_skills = target_skills_analysis(jobs)

    latest_match_by_job: dict[int, int] = {}
    for analysis in analyses:
        if analysis.job_id not in latest_match_by_job:
            latest_match_by_job[analysis.job_id] = int(analysis.score)
    recent_jobs = [
        RecentJob(
            id=item.id,
            job_title=item.job_title,
            analysis_engine=item.analysis_engine,
            created_at=item.created_at,
            match_score=latest_match_by_job.get(item.id),
        )
        for item in jobs[:5]
    ]

    trends = DashboardTrends(
        match_scores=_trend_points(list(reversed(analyses[:6])), "score"),
        interview_scores=_trend_points(list(reversed(evaluations[:6])), "overall_score"),
    )

    has_data = bool(resumes or jobs or analyses or roadmaps or interviews)
    return DashboardData(
        has_data=has_data,
        overview=overview,
        readiness=readiness,
        skill_analysis=skill_analysis,
        learning_progress=learning_progress,
        interview=interview_stats,
        recent_jobs=recent_jobs,
        target_skills=target_skills,
        trends=trends,
    )
