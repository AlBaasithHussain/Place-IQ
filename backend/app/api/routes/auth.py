"""Authentication endpoints: register, login, me, logout."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.auth import AuthResponse, UserCreate, UserLogin, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserPublic.model_validate(user),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> AuthResponse:
    """Create a new account, an empty student profile, and return a JWT."""
    email = str(payload.email).lower()
    if db.query(User).filter(func.lower(User.email) == email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.flush()  # assign user.id without committing yet
        db.add(StudentProfile(user_id=user.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    db.refresh(user)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> AuthResponse:
    """Verify credentials and return a JWT."""
    email = str(payload.email).lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _auth_response(user)


@router.get("/me", response_model=UserPublic)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's public profile."""
    return current_user


@router.post("/logout")
def logout(_current_user: User = Depends(get_current_user)) -> dict:
    """Stateless logout.

    JWTs cannot be un-issued server-side without a token blacklist (planned for
    a later phase). The client must discard the token. We still require a valid
    token so the call itself is authenticated.
    """
    return {"detail": "Logged out. Discard the access token on the client."}
