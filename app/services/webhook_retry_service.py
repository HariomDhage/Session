"""Webhook retry service with exponential backoff."""
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import async_session_maker
from app.models.webhook_queue import WebhookQueueItem
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WebhookRetryService:
    """
    Service for managing webhook retries with exponential backoff.

    Retry schedule (base delay * 4^attempt):
    - Attempt 1: immediate
    - Attempt 2: 4 seconds
    - Attempt 3: 16 seconds
    - After 3 attempts: marked as failed
    """

    BASE_DELAY_SECONDS = 4
    MAX_ATTEMPTS = 3
    RETRY_INTERVAL_SECONDS = 5  # How often to check for retries

    def __init__(self):
        self.is_running = False
        self.webhook_url = settings.WEBHOOK_URL
        self.timeout = settings.WEBHOOK_TIMEOUT
        self.enabled = settings.WEBHOOK_ENABLED

    async def queue_webhook(
        self,
        db: AsyncSession,
        payload: dict,
        event_type: str,
        session_id: Optional[str] = None
    ) -> WebhookQueueItem:
        """Add a webhook to the retry queue."""
        item = WebhookQueueItem(
            url=self.webhook_url,
            payload=json.dumps(payload),
            event_type=event_type,
            session_id=session_id,
            status="pending",
            next_retry_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)

        logger.info(f"Queued webhook: {event_type} for session {session_id}")
        return item

    async def send_with_retry(
        self,
        db: AsyncSession,
        payload: dict,
        event_type: str,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Try to send webhook immediately, queue for retry if failed.

        Returns True if sent successfully, False if queued for retry.
        """
        if not self.enabled:
            logger.info("Webhooks disabled, skipping")
            return True

        # Try immediate send
        success, error = await self._send_webhook(payload)

        if success:
            logger.info(f"Webhook sent successfully: {event_type}")
            return True

        # Queue for retry
        item = WebhookQueueItem(
            url=self.webhook_url,
            payload=json.dumps(payload),
            event_type=event_type,
            session_id=session_id,
            status="pending",
            attempts=1,
            last_attempt_at=datetime.now(timezone.utc).isoformat(),
            last_error=error,
            next_retry_at=self._calculate_next_retry(1),
        )
        db.add(item)
        await db.commit()

        logger.warning(f"Webhook failed, queued for retry: {event_type} - {error}")
        return False

    async def _send_webhook(self, payload: dict) -> tuple[bool, Optional[str]]:
        """Attempt to send a webhook. Returns (success, error_message)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
            return True, None

        except httpx.TimeoutException:
            return False, "Timeout"
        except httpx.HTTPStatusError as e:
            return False, f"HTTP {e.response.status_code}"
        except httpx.RequestError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def _calculate_next_retry(self, attempt: int) -> str:
        """Calculate next retry time using exponential backoff."""
        delay_seconds = self.BASE_DELAY_SECONDS * (4 ** (attempt - 1))
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        return next_retry.isoformat()

    async def process_retry_queue(self):
        """Process pending webhooks that are due for retry."""
        async with async_session_maker() as db:
            try:
                now = datetime.now(timezone.utc).isoformat()

                # Get pending items due for retry
                result = await db.execute(
                    select(WebhookQueueItem)
                    .where(
                        WebhookQueueItem.status == "pending",
                        WebhookQueueItem.next_retry_at <= now
                    )
                    .limit(10)  # Process in batches
                )
                items = result.scalars().all()

                for item in items:
                    await self._process_single_retry(db, item)

            except Exception as e:
                logger.error(f"Error processing retry queue: {e}")

    async def _process_single_retry(self, db: AsyncSession, item: WebhookQueueItem):
        """Process a single retry item."""
        try:
            payload = json.loads(item.payload)
            success, error = await self._send_webhook(payload)

            item.attempts += 1
            item.last_attempt_at = datetime.now(timezone.utc).isoformat()

            if success:
                item.status = "success"
                logger.info(
                    f"Webhook retry successful: {item.event_type} "
                    f"(attempt {item.attempts})"
                )
            elif item.attempts >= self.MAX_ATTEMPTS:
                item.status = "failed"
                item.last_error = error
                logger.error(
                    f"Webhook permanently failed after {item.attempts} attempts: "
                    f"{item.event_type} - {error}"
                )
            else:
                item.last_error = error
                item.next_retry_at = self._calculate_next_retry(item.attempts)
                logger.warning(
                    f"Webhook retry failed, scheduling next attempt: "
                    f"{item.event_type} (attempt {item.attempts}/{self.MAX_ATTEMPTS})"
                )

            await db.commit()

        except Exception as e:
            logger.error(f"Error processing retry item: {e}")
            await db.rollback()

    async def start_retry_worker(self):
        """Start the background retry worker."""
        self.is_running = True
        logger.info("Starting webhook retry worker...")

        while self.is_running:
            try:
                await self.process_retry_queue()
            except Exception as e:
                logger.error(f"Retry worker error: {e}")

            await asyncio.sleep(self.RETRY_INTERVAL_SECONDS)

    def stop_retry_worker(self):
        """Stop the background retry worker."""
        self.is_running = False
        logger.info("Stopping webhook retry worker...")

    async def get_queue_stats(self) -> dict:
        """Get statistics about the webhook queue."""
        async with async_session_maker() as db:
            from sqlalchemy import func

            # Count by status
            result = await db.execute(
                select(
                    WebhookQueueItem.status,
                    func.count(WebhookQueueItem.id)
                )
                .group_by(WebhookQueueItem.status)
            )

            stats = {row[0]: row[1] for row in result}

            return {
                "pending": stats.get("pending", 0),
                "success": stats.get("success", 0),
                "failed": stats.get("failed", 0),
                "retry_interval_seconds": self.RETRY_INTERVAL_SECONDS,
                "max_attempts": self.MAX_ATTEMPTS,
            }


# Global instance
webhook_retry_service = WebhookRetryService()
