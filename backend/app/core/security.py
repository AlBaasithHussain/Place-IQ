"""Password hashing (bcrypt) and JWT access tokens (PyJWT)."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import JWT_AUDIENCE, JWT_ISSUER, settings

# bcrypt only considers the first 72 bytes of a password. We reject longer
# inputs at the schema layer; this constant documents the hard limit.
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash (never store the plain password)."""
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        raise ValueError("Password must be at most 72 bytes")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time comparison of a candidate password against a hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int) -> str:
    """Create a signed JWT whose `sub` claim is the user id."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "aud": JWT_AUDIENCE,
        "iss": JWT_ISSUER,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode + verify a JWT. Raises jwt exceptions on failure."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"require": ["sub", "iat", "exp", "aud", "iss"]},
    )
