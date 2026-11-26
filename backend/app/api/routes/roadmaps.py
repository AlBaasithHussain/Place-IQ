"""Personalised roadmap endpoints (all protected)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.analysis import MatchAnalysis
from app.models.job import Job
from app.models.resume import Resume
from app.models.roadmap import Roadmap, RoadmapTask
from app.models.user import User
from app.schemas.analysis import MatchResult
from app.schemas.roadmap import (
    PriorityLevel,
    RoadmapDetail,
    RoadmapGenerateRequest,
    RoadmapSummary,
    RoadmapTaskDetail,
    RoadmapTaskUpdate,
)
from app.services.resume.skills import collect_resume_skills
from app.services.roadmaps import generator
from app.services.roadmaps.generator import RoadmapGenerationError, RoadmapInput

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])

_LEVEL_BY_REQUIREMENT = {
    "required": PriorityLevel.HIGH,
    "preferred": PriorityLevel.MEDIUM,
    "soft": PriorityLevel.LOW,
}


def _progress(row: Roadmap) -> tuple[int, int, int]:
    tasks = sorted(row.tasks, key=lambda task: task.day)
    completed = sum(1 for task in tasks if task.completed)
    total_minutes = sum(task.estimated_minutes for task in tasks)
    percentage = int((completed / len(tasks)) * 100 + 0.5) if tasks else 0
    return completed, total_minutes, percentage


def _detail(row: Roadmap) -> RoadmapDetail:
    completed, total_minutes, percentage = _progress(row)
    return RoadmapDetail(
        id=row.id,
        user_id=row.user_id,
        resume_id=row.resume_id,
        job_id=row.job_id,
        analysis_id=row.analysis_id,
        job_title=row.job_title,
        match_score=row.match_score,
        duration_days=row.duration_days,
        hours_per_day=row.hours_per_day,
        generation_engine=row.generation_engine,
        priority_skills=row.priority_skills,
        summary=row.summary,
        created_at=row.created_at,
        tasks=[RoadmapTaskDetail.model_validate(task) for task in sorted(row.tasks, key=lambda t: t.day)],
        total_estimated_minutes=total_minutes,
        completed_count=completed,
        progress_percentage=percentage,
    )


def _summary(row: Roadmap) -> RoadmapSummary:
    _, _, percentage = _progress(row)
    return RoadmapSummary(
        id=row.id,
        analysis_id=row.analysis_id,
        job_title=row.job_title,
        match_score=row.match_score,
        duration_days=row.duration_days,
        generation_engine=row.generation_engine,
        created_at=row.created_at,
        progress_percentage=percentage,
    )


@router.post("/generate", response_model=RoadmapDetail, status_code=status.HTTP_201_CREATED)
def generate_roadmap(
    payload: RoadmapGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoadmapDetail:
    analysis = (
        db.query(MatchAnalysis)
        .filter(
            MatchAnalysis.id == payload.analysis_id,
            MatchAnalysis.user_id == current_user.id,
        )
        .first()
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    resume = (
        db.query(Resume)
        .filter(Resume.id == analysis.resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    job = (
        db.query(Job)
        .filter(Job.id == analysis.job_id, Job.user_id == current_user.id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    match_result = MatchResult.model_validate(analysis.result)
    priority_map: dict[str, PriorityLevel] = {}
    for comparison in match_result.comparisons:
        if comparison.status.value in {"missing", "partial"}:
            priority_map[comparison.skill] = _LEVEL_BY_REQUIREMENT.get(
                comparison.requirement_type.value,
                PriorityLevel.MEDIUM,
            )

    data = RoadmapInput(
        job_title=job.job_title,
        required_skills=list(job.required_skills or []),
        missing_skills=match_result.missing_skills,
        partial_skills=match_result.partial_skills,
        resume_skills=collect_resume_skills(resume),
        match_score=analysis.score,
        duration_days=payload.duration_days,
        hours_per_day=payload.hours_per_day,
        priority_map=priority_map,
    )
    try:
        plan, engine = generator.generate_roadmap(data)
    except RoadmapGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service failed. Please try again.",
        ) from exc

    row = Roadmap(
        user_id=current_user.id,
        resume_id=resume.id,
        job_id=job.id,
        analysis_id=analysis.id,
        job_title=job.job_title,
        match_score=analysis.score,
        duration_days=payload.duration_days,
        hours_per_day=payload.hours_per_day,
        generation_engine=engine,
        priority_skills=plan.priority_skills,
        summary=plan.summary,
    )
    for item in plan.days:
        row.tasks.append(
            RoadmapTask(
                day=item.day,
                title=item.title,
                priority=item.priority.value,
                estimated_minutes=item.estimated_minutes,
                learning_topics=item.learning_topics,
                practice_tasks=item.practice_tasks,
                mini_project=item.mini_project,
            )
        )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _detail(row)


@router.get("", response_model=list[RoadmapSummary])
def list_roadmaps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RoadmapSummary]:
    rows = (
        db.query(Roadmap)
        .filter(Roadmap.user_id == current_user.id)
        .order_by(Roadmap.created_at.desc(), Roadmap.id.desc())
        .all()
    )
    return [_summary(row) for row in rows]


@router.get("/{roadmap_id}", response_model=RoadmapDetail)
def get_roadmap(
    roadmap_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoadmapDetail:
    row = (
        db.query(Roadmap)
        .filter(Roadmap.id == roadmap_id, Roadmap.user_id == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")
    return _detail(row)


@router.patch("/{roadmap_id}/tasks/{task_id}", response_model=RoadmapDetail)
def update_task_completion(
    roadmap_id: int,
    task_id: int,
    payload: RoadmapTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoadmapDetail:
    row = (
        db.query(Roadmap)
        .filter(Roadmap.id == roadmap_id, Roadmap.user_id == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")

    task = (
        db.query(RoadmapTask)
        .filter(RoadmapTask.id == task_id, RoadmapTask.roadmap_id == row.id)
        .first()
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.completed = payload.completed
    task.completed_at = datetime.now(timezone.utc) if payload.completed else None
    db.commit()
    db.refresh(row)
    return _detail(row)
