"""Manual and ManualStep database models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Manual(Base):
    """Instruction manual model."""

    __tablename__ = "manuals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manual_id = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    total_steps = Column(Integer, nullable=False)
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
    steps = relationship(
        "ManualStep",
        back_populates="manual",
        cascade="all, delete-orphan",
        order_by="ManualStep.step_number"
    )
    sessions = relationship("Session", back_populates="manual")

    def __repr__(self):
        return f"<Manual(manual_id='{self.manual_id}', title='{self.title}', total_steps={self.total_steps})>"


class ManualStep(Base):
    """Individual step within a manual."""

    __tablename__ = "manual_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manual_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("manuals.id", ondelete="CASCADE"),
        nullable=False
    )
    step_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(
        String(50),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Relationships
    manual = relationship("Manual", back_populates="steps")

    __table_args__ = (
        UniqueConstraint("manual_uuid", "step_number", name="uq_manual_step_number"),
        Index("idx_manual_steps_manual_id", "manual_uuid"),
        Index("idx_manual_steps_step_number", "manual_uuid", "step_number"),
    )

    def __repr__(self):
        return f"<ManualStep(step_number={self.step_number}, title='{self.title}')>"
