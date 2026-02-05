"""Analytics API routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """
    Get overall system statistics.

    Returns counts of sessions (total, active, completed, abandoned),
    manuals, messages, and key metrics like completion rate.
    """
    service = AnalyticsService(db)
    return await service.get_overview_stats()


@router.get("/popular-manuals")
async def get_popular_manuals(
    limit: int = Query(default=5, ge=1, le=20, description="Number of manuals to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get most popular manuals by session count.

    Returns manuals ordered by number of sessions, with completion rates.
    """
    service = AnalyticsService(db)
    return await service.get_popular_manuals(limit=limit)


@router.get("/recent-activity")
async def get_recent_activity(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity statistics for a time period.

    Returns counts of new sessions, completions, progress updates,
    and messages in the specified time window.
    """
    service = AnalyticsService(db)
    return await service.get_recent_activity(hours=hours)


@router.get("/users/{user_id}")
async def get_user_stats(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics for a specific user.

    Returns session counts and message totals for the user.
    """
    service = AnalyticsService(db)
    return await service.get_user_stats(user_id)


@router.get("/manuals/{manual_id}/steps")
async def get_step_analytics(
    manual_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get step-by-step analytics for a manual.

    Returns completion rates and attempt counts for each step.
    Useful for identifying where users struggle or drop off.
    """
    service = AnalyticsService(db)
    return await service.get_step_analytics(manual_id)
