"""Background task service for automated maintenance."""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import update, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models import Session
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BackgroundTaskService:
    """Service for running background maintenance tasks."""

    def __init__(self):
        self.is_running = False
        self.cleanup_interval_seconds = 300  # Run every 5 minutes
        self.session_timeout_minutes = 30  # Mark sessions as abandoned after 30 min inactivity
        self.webhook_retry_task = None

    async def start(self):
        """Start background task loop."""
        self.is_running = True
        logger.info("Starting background task service...")

        # Start webhook retry worker
        from app.services.webhook_retry_service import webhook_retry_service
        self.webhook_retry_task = asyncio.create_task(
            webhook_retry_service.start_retry_worker()
        )
        logger.info("Started webhook retry worker")

        while self.is_running:
            try:
                await self.cleanup_stale_sessions()
            except Exception as e:
                logger.error(f"Error in background task: {e}")

            await asyncio.sleep(self.cleanup_interval_seconds)

    def stop(self):
        """Stop background task loop."""
        self.is_running = False
        logger.info("Stopping background task service...")

        # Stop webhook retry worker
        from app.services.webhook_retry_service import webhook_retry_service
        webhook_retry_service.stop_retry_worker()
        if self.webhook_retry_task:
            self.webhook_retry_task.cancel()
        logger.info("Stopped webhook retry worker")

    async def cleanup_stale_sessions(self):
        """
        Mark sessions as abandoned if no activity for configured timeout.

        This handles edge case where users abandon sessions without
        explicitly ending them.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.session_timeout_minutes)
        cutoff_str = cutoff.isoformat()

        async with async_session_maker() as db:
            try:
                # Find and update stale sessions
                result = await db.execute(
                    update(Session)
                    .where(
                        Session.status == "active",
                        Session.last_activity_at < cutoff_str
                    )
                    .values(
                        status="abandoned",
                        ended_at=datetime.now(timezone.utc).isoformat(),
                        updated_at=datetime.now(timezone.utc).isoformat()
                    )
                    .returning(Session.session_id)
                )

                abandoned_sessions = result.scalars().all()
                await db.commit()

                if abandoned_sessions:
                    logger.info(
                        f"Marked {len(abandoned_sessions)} sessions as abandoned due to inactivity: "
                        f"{abandoned_sessions[:5]}{'...' if len(abandoned_sessions) > 5 else ''}"
                    )

            except Exception as e:
                logger.error(f"Failed to cleanup stale sessions: {e}")
                await db.rollback()

    async def get_stats(self) -> dict:
        """Get background task statistics."""
        async with async_session_maker() as db:
            # Count active sessions
            active_count = await db.execute(
                select(func.count(Session.id)).where(Session.status == "active")
            )

            # Count sessions at risk of timeout (activity > 20 min ago)
            risk_cutoff = datetime.now(timezone.utc) - timedelta(minutes=20)
            at_risk = await db.execute(
                select(func.count(Session.id))
                .where(
                    Session.status == "active",
                    Session.last_activity_at < risk_cutoff.isoformat()
                )
            )

            # Get webhook retry stats
            try:
                from app.services.webhook_retry_service import webhook_retry_service
                webhook_stats = await webhook_retry_service.get_queue_stats()
            except Exception:
                webhook_stats = {"error": "Unable to get stats"}

            return {
                "is_running": self.is_running,
                "cleanup_interval_seconds": self.cleanup_interval_seconds,
                "session_timeout_minutes": self.session_timeout_minutes,
                "active_sessions": active_count.scalar() or 0,
                "sessions_at_risk_of_timeout": at_risk.scalar() or 0,
                "webhook_retry_queue": webhook_stats,
            }


# Global instance
background_service = BackgroundTaskService()
