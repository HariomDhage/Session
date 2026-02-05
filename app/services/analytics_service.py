"""Analytics service for dashboard statistics and insights."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, func, case, and_, cast
from sqlalchemy.types import DateTime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session, Manual, ConversationMessage, ProgressEvent

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating analytics and statistics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overview_stats(self) -> dict:
        """Get overall system statistics."""
        # Session counts by status
        session_stats = await self.db.execute(
            select(
                func.count(Session.id).label("total"),
                func.sum(case((Session.status == "active", 1), else_=0)).label("active"),
                func.sum(case((Session.status == "completed", 1), else_=0)).label("completed"),
                func.sum(case((Session.status == "abandoned", 1), else_=0)).label("abandoned"),
            )
        )
        stats = session_stats.one()

        # Manual count
        manual_count = await self.db.execute(select(func.count(Manual.id)))
        total_manuals = manual_count.scalar() or 0

        # Message count
        message_count = await self.db.execute(select(func.count(ConversationMessage.id)))
        total_messages = message_count.scalar() or 0

        # Average completion rate
        total = stats.total or 0
        completed = stats.completed or 0
        completion_rate = (completed / total * 100) if total > 0 else 0

        # Average session duration for completed sessions
        # Note: started_at and ended_at are stored as ISO strings
        duration_result = await self.db.execute(
            select(func.avg(
                func.extract('epoch',
                    cast(Session.ended_at, DateTime) -
                    cast(Session.started_at, DateTime)
                )
            )).where(Session.status == "completed", Session.ended_at.isnot(None))
        )
        avg_duration = duration_result.scalar() or 0

        return {
            "sessions": {
                "total": stats.total or 0,
                "active": stats.active or 0,
                "completed": stats.completed or 0,
                "abandoned": stats.abandoned or 0,
            },
            "manuals": {
                "total": total_manuals,
            },
            "messages": {
                "total": total_messages,
            },
            "metrics": {
                "completion_rate_percent": round(completion_rate, 2),
                "avg_session_duration_seconds": round(avg_duration, 2) if avg_duration else 0,
            }
        }

    async def get_popular_manuals(self, limit: int = 5) -> list:
        """Get most popular manuals by session count."""
        result = await self.db.execute(
            select(
                Manual.manual_id,
                Manual.title,
                Manual.total_steps,
                func.count(Session.id).label("session_count"),
                func.sum(case((Session.status == "completed", 1), else_=0)).label("completed_count"),
            )
            .join(Session, Session.manual_uuid == Manual.id)
            .group_by(Manual.id)
            .order_by(func.count(Session.id).desc())
            .limit(limit)
        )

        manuals = []
        for row in result:
            completion_rate = (row.completed_count / row.session_count * 100) if row.session_count > 0 else 0
            manuals.append({
                "manual_id": row.manual_id,
                "title": row.title,
                "total_steps": row.total_steps,
                "session_count": row.session_count,
                "completed_count": row.completed_count or 0,
                "completion_rate_percent": round(completion_rate, 2),
            })

        return manuals

    async def get_recent_activity(self, hours: int = 24) -> dict:
        """Get activity statistics for the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()

        # New sessions in time period
        new_sessions = await self.db.execute(
            select(func.count(Session.id))
            .where(Session.created_at >= cutoff_str)
        )

        # Completed sessions in time period
        completed_sessions = await self.db.execute(
            select(func.count(Session.id))
            .where(
                Session.status == "completed",
                Session.ended_at >= cutoff_str
            )
        )

        # Progress events in time period
        progress_events = await self.db.execute(
            select(func.count(ProgressEvent.id))
            .where(ProgressEvent.created_at >= cutoff_str)
        )

        # Messages in time period
        messages = await self.db.execute(
            select(func.count(ConversationMessage.id))
            .where(ConversationMessage.created_at >= cutoff_str)
        )

        return {
            "time_period_hours": hours,
            "new_sessions": new_sessions.scalar() or 0,
            "completed_sessions": completed_sessions.scalar() or 0,
            "progress_updates": progress_events.scalar() or 0,
            "messages": messages.scalar() or 0,
        }

    async def get_user_stats(self, user_id: str) -> dict:
        """Get statistics for a specific user."""
        # User's sessions
        session_stats = await self.db.execute(
            select(
                func.count(Session.id).label("total"),
                func.sum(case((Session.status == "active", 1), else_=0)).label("active"),
                func.sum(case((Session.status == "completed", 1), else_=0)).label("completed"),
            )
            .where(Session.user_id == user_id)
        )
        stats = session_stats.one()

        # User's message count
        message_count = await self.db.execute(
            select(func.count(ConversationMessage.id))
            .join(Session, ConversationMessage.session_uuid == Session.id)
            .where(Session.user_id == user_id)
        )

        return {
            "user_id": user_id,
            "sessions": {
                "total": stats.total or 0,
                "active": stats.active or 0,
                "completed": stats.completed or 0,
            },
            "total_messages": message_count.scalar() or 0,
        }

    async def get_step_analytics(self, manual_id: str) -> dict:
        """Get step-by-step analytics for a manual."""
        # Get manual
        manual_result = await self.db.execute(
            select(Manual).where(Manual.manual_id == manual_id)
        )
        manual = manual_result.scalar_one_or_none()

        if not manual:
            return {"error": f"Manual '{manual_id}' not found"}

        # Get completion count per step
        step_stats = await self.db.execute(
            select(
                ProgressEvent.step_number,
                func.count(ProgressEvent.id).label("attempts"),
                func.sum(case((ProgressEvent.step_status == "DONE", 1), else_=0)).label("completions"),
            )
            .join(Session, ProgressEvent.session_uuid == Session.id)
            .where(Session.manual_uuid == manual.id)
            .group_by(ProgressEvent.step_number)
            .order_by(ProgressEvent.step_number)
        )

        steps = []
        for row in step_stats:
            completion_rate = (row.completions / row.attempts * 100) if row.attempts > 0 else 0
            steps.append({
                "step_number": row.step_number,
                "attempts": row.attempts,
                "completions": row.completions or 0,
                "completion_rate_percent": round(completion_rate, 2),
            })

        return {
            "manual_id": manual_id,
            "title": manual.title,
            "total_steps": manual.total_steps,
            "step_analytics": steps,
        }
