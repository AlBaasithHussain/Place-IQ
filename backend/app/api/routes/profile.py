"""Student profile endpoints (protected)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.profile import ProfilePublic, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=ProfilePublic)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudentProfile:
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.put("/me", response_model=ProfilePublic)
def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudentProfile:
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        profile = StudentProfile(user_id=current_user.id)
        db.add(profile)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile
