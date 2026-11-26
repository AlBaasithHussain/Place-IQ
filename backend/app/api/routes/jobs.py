"""Job description analysis endpoints (all protected)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobAnalyzeRequest, JobDetail, JobSummary
from app.services.jobs import analyzer

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/analyze", response_model=JobDetail, status_code=status.HTTP_201_CREATED)
def analyze_job_description(
    payload: JobAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    try:
        result, engine = analyzer.analyze_job_description(payload.text)
    except analyzer.JobAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service failed. Please try again.",
        ) from exc

    job = Job(
        user_id=current_user.id,
        original_text=payload.text,
        analysis_engine=engine,
        **result.model_dump(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobSummary])
def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Job]:
    return (
        db.query(Job)
        .filter(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .all()
    )


@router.get("/{job_id}", response_model=JobDetail)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.user_id == current_user.id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
