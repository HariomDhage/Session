"""API routes."""
from fastapi import APIRouter
from app.api.routes import sessions, messages, progress, manuals, analytics

api_router = APIRouter()

api_router.include_router(
    manuals.router,
    prefix="/manuals",
    tags=["Manuals"]
)

api_router.include_router(
    sessions.router,
    prefix="/sessions",
    tags=["Sessions"]
)

api_router.include_router(
    messages.router,
    prefix="/sessions",
    tags=["Messages"]
)

api_router.include_router(
    progress.router,
    prefix="/sessions",
    tags=["Progress"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"]
)
