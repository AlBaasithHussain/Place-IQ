"""Database connectivity using psycopg2 (the PostgreSQL driver).

Phase 1 only needs a lightweight connection + health ping. The SQLAlchemy ORM
layer (models, sessions, migrations) is introduced in Phase 2 and can reuse the
same DATABASE_URL.
"""

from collections.abc import Generator
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import connection as PgConnection
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


@contextmanager
def get_connection() -> Generator[PgConnection, None, None]:
    """Open a short-lived PostgreSQL connection and always close it."""
    conn = psycopg2.connect(settings.DATABASE_URL, connect_timeout=3)
    try:
        yield conn
    finally:
        conn.close()


def check_database() -> bool:
    """Return True if a trivial query succeeds; raise on any failure."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
