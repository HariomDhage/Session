"""ConversationMessage and ProgressEvent database models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class ConversationMessage(Base):
    """Conversation message within a session."""

    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    message_text = Column(Text, nullable=False)
    sender = Column(String(20), nullable=False)  # 'user', 'agent', 'system'
    step_at_time = Column(Integer, nullable=True)  # Which step user was on
    created_at = Column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Relationships
    session = relationship("Session", back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            "sender IN ('user', 'agent', 'system')",
            name="check_valid_sender"
        ),
        Index("idx_messages_session_id", "session_uuid"),
        Index("idx_messages_created_at", "session_uuid", "created_at"),
    )

    def __repr__(self):
        return f"<ConversationMessage(sender='{self.sender}', step={self.step_at_time})>"


class ProgressEvent(Base):
    """Progress event for audit trail and idempotency."""

    __tablename__ = "progress_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    step_number = Column(Integer, nullable=False)
    step_status = Column(String(20), nullable=False)  # 'DONE', 'ONGOING'
    previous_step = Column(Integer, nullable=True)
    processed = Column(Boolean, nullable=False, default=False)
    idempotency_key = Column(String(100), nullable=True)
    created_at = Column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Relationships
    session = relationship("Session", back_populates="progress_events")

    __table_args__ = (
        CheckConstraint(
            "step_status IN ('DONE', 'ONGOING')",
            name="check_valid_step_status"
        ),
        UniqueConstraint(
            "session_uuid",
            "idempotency_key",
            name="uq_session_idempotency_key"
        ),
        Index("idx_progress_events_session_id", "session_uuid"),
        Index("idx_progress_events_idempotency", "idempotency_key"),
    )

    def __repr__(self):
        return f"<ProgressEvent(step={self.step_number}, status='{self.step_status}')>"
