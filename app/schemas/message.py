"""Pydantic schemas for Message operations."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class SenderType(str, Enum):
    """Message sender type enumeration."""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class MessageCreate(BaseModel):
    """Schema for creating a message (Type A input)."""

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User identifier"
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Message content"
    )
    sender: SenderType = Field(
        ...,
        description="Who sent this message (user, agent, or system)"
    )


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: UUID
    session_id: str
    message: str
    sender: str
    step_at_time: Optional[int] = None
    created_at: str

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Schema for listing messages."""

    messages: List[MessageResponse]
    total: int
    session_id: str
