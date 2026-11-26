"""Health endpoints used by the frontend status badge and uptime checks."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.db.connection import check_database

router = APIRouter()
logger = logging.getLogger("app.health")


@router.get("/health")
def health_check() -> dict:
    """Liveness check: the API process is up and serving requests."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/db")
def health_db() -> dict:
    """Readiness check: can we actually reach PostgreSQL?

    Returns HTTP 200 with status="degraded" if the DB is unreachable so the UI
    can show a warning without the whole request failing.
    """
    try:
        check_database()
        return {"status": "ok", "database": "connected"}
    except Exception as exc:  # noqa: BLE001 - report any driver/connection error
        logger.warning("Database health check failed: %s", exc)
        return {"status": "degraded", "database": "unavailable"}
