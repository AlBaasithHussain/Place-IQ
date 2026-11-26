"""Database engine, session factory and declarative base (SQLAlchemy 1.4).

SQLAlchemy 1.4 is used because SQLAlchemy 2.x's mandatory compiled C extensions
are blocked by Windows Application Control on this machine. 1.4 provides a
pure-Python fallback and full ORM support. The code below is written to be
forward-compatible with the 2.0 Session style (`future=True`).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    _connect_args: dict = {"check_same_thread": False}
else:
    _connect_args = {"connect_timeout": 3}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a session and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
