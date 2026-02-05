"""Pydantic schemas for Progress operations."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class StepStatus(str, Enum):
    """Step status enumeration."""

    DONE = "DONE"
    ONGOING = "ONGOING"


class ProgressUpdate(BaseModel):
    """Schema for progress update (Type B & C input)."""

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User identifier"
    )
    current_step: int = Field(
        ...,
        ge=1,
        description="Current step number (1-indexed)"
    )
    step_status: StepStatus = Field(
        ...,
        description="Step status - DONE increments counter, ONGOING does not"
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional idempotency key to prevent duplicate processing"
    )


class NextStepInfo(BaseModel):
    """Schema for next step information."""

    step_number: int
    title: str
    content: str


class ProgressResponse(BaseModel):
    """Schema for progress update response."""

    session_id: str
    user_id: str
    previous_step: int
    current_step: int
    total_steps: int
    status: str
    next_step: Optional[NextStepInfo] = None
    feedback_sent: bool = False
    message: str


class NextStepResponse(BaseModel):
    """Schema for getting next step recommendation."""

    session_id: str
    current_step: int
    total_steps: int
    is_completed: bool
    next_step: Optional[NextStepInfo] = None
    message: str


class DuplicateProgressResponse(BaseModel):
    """Schema for duplicate progress update response."""

    status: str = "already_processed"
    message: str
    session_id: str
    idempotency_key: str
