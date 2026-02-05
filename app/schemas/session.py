"""Pydantic schemas for Session operations."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enumeration."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class SessionCreate(BaseModel):
    """Schema for creating a session."""

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique session identifier"
    )
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User identifier"
    )
    manual_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Manual identifier to use for this session"
    )


class SessionUpdate(BaseModel):
    """Schema for updating a session."""

    status: Optional[SessionStatus] = Field(
        None,
        description="New session status"
    )


class SessionResponse(BaseModel):
    """Schema for session response."""

    id: UUID
    session_id: str
    user_id: str
    manual_id: str
    current_step: int
    total_steps: int
    status: str
    started_at: str
    ended_at: Optional[str] = None
    last_activity_at: str
    duration_seconds: Optional[float] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Schema for listing sessions."""

    sessions: List[SessionResponse]
    total: int


class SessionDeleteResponse(BaseModel):
    """Schema for session deletion response."""

    message: str
    session_id: str
