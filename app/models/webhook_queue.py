"""Webhook queue model for retry mechanism."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class WebhookQueueItem(Base):
    """Queued webhook for retry."""

    __tablename__ = "webhook_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(500), nullable=False)
    payload = Column(Text, nullable=False)  # JSON string
    event_type = Column(String(50), nullable=False)
    session_id = Column(String(100), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    last_attempt_at = Column(String(50), nullable=True)
    last_error = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, success, failed
    created_at = Column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat()
    )
    next_retry_at = Column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat()
    )

    __table_args__ = (
        Index("idx_webhook_queue_status", "status"),
        Index("idx_webhook_queue_next_retry", "status", "next_retry_at"),
    )

    def __repr__(self):
        return f"<WebhookQueueItem(event_type='{self.event_type}', status='{self.status}', attempts={self.attempts})>"
