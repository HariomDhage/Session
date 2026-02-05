"""Pydantic schemas for Manual operations."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ManualStepCreate(BaseModel):
    """Schema for creating a manual step."""

    step_number: int = Field(..., ge=1, description="Step number (1-indexed)")
    title: str = Field(..., min_length=1, max_length=255, description="Step title")
    content: str = Field(..., min_length=1, description="Step content/instructions")


class ManualStepResponse(BaseModel):
    """Schema for manual step response."""

    id: UUID
    step_number: int
    title: str
    content: str
    created_at: str

    class Config:
        from_attributes = True


class ManualCreate(BaseModel):
    """Schema for creating a manual."""

    manual_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique manual identifier"
    )
    title: str = Field(..., min_length=1, max_length=255, description="Manual title")
    steps: List[ManualStepCreate] = Field(
        ...,
        min_length=1,
        description="List of steps (minimum 1 step)"
    )

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: List[ManualStepCreate]) -> List[ManualStepCreate]:
        """Validate that step numbers are sequential starting from 1."""
        if not v:
            raise ValueError("Manual must have at least one step")

        step_numbers = [step.step_number for step in v]
        expected = list(range(1, len(v) + 1))

        if sorted(step_numbers) != expected:
            raise ValueError(
                f"Step numbers must be sequential starting from 1. "
                f"Expected {expected}, got {sorted(step_numbers)}"
            )

        return v

    @property
    def total_steps(self) -> int:
        """Get total number of steps."""
        return len(self.steps)


class ManualResponse(BaseModel):
    """Schema for manual response."""

    id: UUID
    manual_id: str
    title: str
    total_steps: int
    steps: List[ManualStepResponse] = []
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ManualListResponse(BaseModel):
    """Schema for listing manuals."""

    manuals: List[ManualResponse]
    total: int
