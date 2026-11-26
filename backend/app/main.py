"""FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.init_db import create_tables

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup if the database is reachable. If Postgres is
    # down the API still boots and /api/v1/health/db reports "degraded".
    try:
        create_tables()
        logger.info("Database tables are ready.")
    except Exception as exc:  # noqa: BLE001 - keep the API bootable
        logger.warning("Skipping DB table creation: %s", exc)
    yield


DOCS_ENABLED = settings.ENVIRONMENT not in {"production", "prod", "staging"}

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if DOCS_ENABLED else None,
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# All versioned API routes are mounted under /api/v1.
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["root"])
def root() -> dict:
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs" if DOCS_ENABLED else None,
        "health": f"{settings.API_V1_STR}/health",
    }
