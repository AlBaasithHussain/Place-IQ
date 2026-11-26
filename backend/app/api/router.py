"""Top-level API router.

Every feature module gets included here so main.py stays small and the API
surface is easy to read at a glance.
"""

from fastapi import APIRouter

from app.api.routes import (
    analysis,
    auth,
    dashboard,
    health,
    interviews,
    jobs,
    profile,
    resumes,
    roadmaps,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(dashboard.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(analysis.router)
api_router.include_router(roadmaps.router)
api_router.include_router(interviews.router)
