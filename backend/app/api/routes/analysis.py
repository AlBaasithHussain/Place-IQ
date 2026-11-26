"""Resume ↔ job comparison endpoints (all protected)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.analysis import MatchAnalysis
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.analysis import AnalysisSummary, MatchDetail, MatchRequest
from app.schemas.job import JobAnalysisResult
from app.services.analysis import scorer
from app.services.resume.skills import collect_resume_skills

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _detail(row: MatchAnalysis) -> MatchDetail:
    return MatchDetail.model_validate(
        {
            "id": row.id,
            "user_id": row.user_id,
            "resume_id": row.resume_id,
            "job_id": row.job_id,
            "created_at": row.created_at,
            **row.result,
        }
    )


@router.post("/match", response_model=MatchDetail, status_code=status.HTTP_201_CREATED)
def match_resume_to_job(
    payload: MatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchDetail:
    resume = (
        db.query(Resume)
        .filter(Resume.id == payload.resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    job = (
        db.query(Job)
        .filter(Job.id == payload.job_id, Job.user_id == current_user.id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job_data = JobAnalysisResult.model_validate(job, from_attributes=True).model_dump()
    parsed = resume.parsed_data or {}
    result = scorer.score_match(
        collect_resume_skills(resume),
        job_data,
        resume_experience=parsed.get("experience", []) or [],
        resume_projects=parsed.get("projects", []) or [],
    )

    row = MatchAnalysis(
        user_id=current_user.id,
        resume_id=resume.id,
        job_id=job.id,
        score=result.score,
        result=result.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _detail(row)


@router.get("", response_model=list[AnalysisSummary])
def list_analyses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AnalysisSummary]:
    rows = (
        db.query(MatchAnalysis)
        .filter(MatchAnalysis.user_id == current_user.id)
        .order_by(MatchAnalysis.created_at.desc(), MatchAnalysis.id.desc())
        .all()
    )
    return [AnalysisSummary.model_validate(row) for row in rows]


@router.get("/{analysis_id}", response_model=MatchDetail)
def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchDetail:
    row = (
        db.query(MatchAnalysis)
        .filter(MatchAnalysis.id == analysis_id, MatchAnalysis.user_id == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return _detail(row)
