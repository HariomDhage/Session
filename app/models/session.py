"""Session database model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Session(Base):
    """User session model."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    manual_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("manuals.id"),
        nullable=False
    )
    current_step = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="active")
    started_at = Column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat()
    )
    ended_at = Column(String(50), nullable=True)
    last_activity_at = Column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat()
    )
    version = Column(Integer, nullable=False, default=1)  # For optimistic locking
    created_at = Column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at = Column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
        onupdate=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Relationships
    manual = relationship("Manual", back_populates="sessions")
    messages = relationship(
        "ConversationMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at"
    )
    progress_events = relationship(
        "ProgressEvent",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ProgressEvent.created_at"
    )

    __table_args__ = (
        CheckConstraint("current_step >= 0", name="check_current_step_positive"),
        CheckConstraint(
            "status IN ('active', 'completed', 'abandoned')",
            name="check_valid_status"
        ),
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_manual_id", "manual_uuid"),
    )

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id='{self.user_id}', current_step={self.current_step})>"

    @property
    def duration_seconds(self) -> float | None:
        """Calculate session duration in seconds."""
        if not self.started_at:
            return None

        start = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))

        if self.ended_at:
            end = datetime.fromisoformat(self.ended_at.replace("Z", "+00:00"))
        else:
            end = datetime.now(timezone.utc)

        return (end - start).total_seconds()
