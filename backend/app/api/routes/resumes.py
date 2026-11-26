"""Resume upload / listing / detail endpoints (all protected)."""

import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ParsedResume, ResumeDetail, ResumeSummary
from app.services.resume.cleaner import clean_text
from app.services.resume.extractor import extract_resume_data
from app.services.resume.pdf import PdfExtractionError, extract_text_from_pdf

router = APIRouter(prefix="/resumes", tags=["resumes"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def sanitize_filename(filename: str) -> str:
    """Keep a safe basename only; never trust client-supplied paths."""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    name = re.sub(r"[\x00-\x1f\x7f<>:|?*]", "", name).strip(" .")
    return name[:200] or "resume.pdf"


@router.post("/upload", response_model=ResumeDetail, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    filename = sanitize_filename(file.filename or "")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed (.pdf)",
        )

    try:
        data = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()

    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty",
        )
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File is too large (maximum is 5 MB)",
        )
    if not data.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The file is not a valid PDF",
        )

    try:
        extracted = extract_text_from_pdf(data)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    cleaned = clean_text(extracted)
    if not cleaned:
        raise HTTPException(
            status_code=422,
            detail="No extractable text found. The PDF may be empty or a scanned image.",
        )

    parsed = ParsedResume.model_validate(extract_resume_data(cleaned))

    resume = Resume(
        user_id=current_user.id,
        original_filename=filename,
        file_size=len(data),
        mime_type="application/pdf",
        raw_text=cleaned,
        parsed_data=parsed.model_dump(),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("", response_model=list[ResumeSummary])
def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResumeSummary]:
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc(), Resume.id.desc())
        .all()
    )
    summaries: list[ResumeSummary] = []
    for resume in resumes:
        parsed = resume.parsed_data or {}
        summaries.append(
            ResumeSummary(
                id=resume.id,
                original_filename=resume.original_filename,
                file_size=resume.file_size,
                created_at=resume.created_at,
                name=parsed.get("name"),
                email=parsed.get("email"),
            )
        )
    return summaries


@router.get("/{resume_id}", response_model=ResumeDetail)
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Resume:
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    return resume
