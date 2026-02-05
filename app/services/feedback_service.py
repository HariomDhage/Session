"""Feedback service for external webhook integration with retry support."""
import logging
from typing import Optional
import httpx

from app.config import get_settings
from app.models import Session, Manual

logger = logging.getLogger(__name__)
settings = get_settings()


class FeedbackService:
    """
    Service for sending feedback to external instruction delivery service.

    Features:
    - Immediate webhook delivery attempt
    - Automatic queuing for retry on failure
    - Exponential backoff (4s, 16s, 64s)
    - Max 3 retry attempts
    """

    def __init__(self):
        self.webhook_url = settings.WEBHOOK_URL
        self.timeout = settings.WEBHOOK_TIMEOUT
        self.enabled = settings.WEBHOOK_ENABLED

    async def send_progress_update(
        self,
        session: Session,
        manual: Manual,
        previous_step: int,
        step_status: str
    ) -> bool:
        """
        Send progress update to external instruction delivery service.

        Args:
            session: The session being updated
            manual: The manual associated with the session
            previous_step: The step before the update
            step_status: The status of the update (DONE/ONGOING)

        Returns:
            True if feedback was sent successfully (or queued), False if disabled
        """
        if not self.enabled:
            logger.info("Webhook disabled, skipping feedback")
            return False

        payload = {
            "event_type": "progress_update",
            "session_id": session.session_id,
            "user_id": session.user_id,
            "manual_id": manual.manual_id,
            "previous_step": previous_step,
            "current_step": session.current_step,
            "total_steps": manual.total_steps,
            "step_status": step_status,
            "session_status": session.status,
            "session_duration_seconds": session.duration_seconds,
            "is_completed": session.current_step > manual.total_steps or session.status == "completed",
        }

        return await self._send_with_retry(
            payload=payload,
            event_type="progress_update",
            session_id=session.session_id
        )

    async def send_session_created(
        self,
        session: Session,
        manual: Manual
    ) -> bool:
        """Send notification when a new session is created."""
        if not self.enabled:
            return False

        payload = {
            "event_type": "session_created",
            "session_id": session.session_id,
            "user_id": session.user_id,
            "manual_id": manual.manual_id,
            "total_steps": manual.total_steps,
        }

        return await self._send_with_retry(
            payload=payload,
            event_type="session_created",
            session_id=session.session_id
        )

    async def send_session_ended(
        self,
        session: Session,
        manual: Manual
    ) -> bool:
        """Send notification when a session ends."""
        if not self.enabled:
            return False

        payload = {
            "event_type": "session_ended",
            "session_id": session.session_id,
            "user_id": session.user_id,
            "manual_id": manual.manual_id,
            "final_step": session.current_step,
            "total_steps": manual.total_steps,
            "status": session.status,
            "duration_seconds": session.duration_seconds,
        }

        return await self._send_with_retry(
            payload=payload,
            event_type="session_ended",
            session_id=session.session_id
        )

    async def _send_with_retry(
        self,
        payload: dict,
        event_type: str,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Send webhook with automatic retry on failure.

        First tries immediate delivery. If that fails, queues for background retry.
        """
        # Try immediate send
        success = await self._send_webhook(payload, event_type, session_id)

        if success:
            return True

        # Queue for retry using background service
        try:
            from app.services.webhook_retry_service import webhook_retry_service
            from app.database import async_session_maker

            async with async_session_maker() as db:
                await webhook_retry_service.queue_webhook(
                    db=db,
                    payload=payload,
                    event_type=event_type,
                    session_id=session_id
                )
            logger.info(f"Queued {event_type} webhook for retry")
            return True  # Return True because it's queued for retry

        except Exception as e:
            logger.error(f"Failed to queue webhook for retry: {e}")
            return False

    async def _send_webhook(
        self,
        payload: dict,
        event_type: str,
        session_id: Optional[str]
    ) -> bool:
        """Attempt immediate webhook delivery."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()

            logger.info(
                f"Sent {event_type} webhook for session '{session_id}'"
            )
            return True

        except httpx.TimeoutException:
            logger.warning(f"Timeout sending {event_type} webhook for '{session_id}'")
            return False
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"HTTP {e.response.status_code} sending {event_type} webhook for '{session_id}'"
            )
            return False
        except httpx.RequestError as e:
            logger.warning(f"Request error sending {event_type} webhook: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook: {e}")
            return False
