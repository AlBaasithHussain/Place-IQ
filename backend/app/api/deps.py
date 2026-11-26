"""Reusable FastAPI dependencies (JWT auth / current user)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer JWT, or raise 401."""
    if credentials is None or not credentials.credentials:
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub", ""))
    except ExpiredSignatureError:
        raise _unauthorized("Token has expired")
    except (InvalidTokenError, ValueError, TypeError):
        raise _unauthorized("Invalid authentication token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise _unauthorized("User no longer exists")
    return user
