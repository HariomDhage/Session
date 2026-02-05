"""Manual service for business logic."""
import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Manual, ManualStep
from app.schemas.manual import ManualCreate, ManualResponse, ManualStepResponse
from app.utils.exceptions import ManualNotFoundError, SessionServiceException

logger = logging.getLogger(__name__)


class ManualService:
    """Service for manual-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_manual(self, manual_data: ManualCreate) -> Manual:
        """Create a new manual with steps."""
        # Check if manual_id already exists
        existing = await self.db.execute(
            select(Manual).where(Manual.manual_id == manual_data.manual_id)
        )
        if existing.scalar_one_or_none():
            raise SessionServiceException(
                f"Manual '{manual_data.manual_id}' already exists",
                status_code=409
            )

        # Create manual
        manual = Manual(
            manual_id=manual_data.manual_id,
            title=manual_data.title,
            total_steps=len(manual_data.steps),
        )
        self.db.add(manual)
        await self.db.flush()  # Get the manual ID

        # Create steps
        for step_data in manual_data.steps:
            step = ManualStep(
                manual_uuid=manual.id,
                step_number=step_data.step_number,
                title=step_data.title,
                content=step_data.content,
            )
            self.db.add(step)

        await self.db.commit()
        await self.db.refresh(manual)

        # Load steps relationship
        result = await self.db.execute(
            select(Manual)
            .where(Manual.id == manual.id)
            .options(selectinload(Manual.steps))
        )
        manual = result.scalar_one()

        logger.info(f"Created manual '{manual.manual_id}' with {manual.total_steps} steps")
        return manual

    async def get_manual_by_id(self, manual_id: str) -> Manual:
        """Get a manual by its external ID."""
        result = await self.db.execute(
            select(Manual)
            .where(Manual.manual_id == manual_id)
            .options(selectinload(Manual.steps))
        )
        manual = result.scalar_one_or_none()

        if not manual:
            raise ManualNotFoundError(manual_id)

        return manual

    async def get_manual_by_uuid(self, manual_uuid: UUID) -> Manual:
        """Get a manual by its internal UUID."""
        result = await self.db.execute(
            select(Manual)
            .where(Manual.id == manual_uuid)
            .options(selectinload(Manual.steps))
        )
        manual = result.scalar_one_or_none()

        if not manual:
            raise ManualNotFoundError(str(manual_uuid))

        return manual

    async def list_manuals(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Manual], int]:
        """List all manuals with pagination."""
        # Get total count
        count_result = await self.db.execute(select(Manual))
        total = len(count_result.scalars().all())

        # Get paginated results
        result = await self.db.execute(
            select(Manual)
            .options(selectinload(Manual.steps))
            .offset(skip)
            .limit(limit)
            .order_by(Manual.created_at.desc())
        )
        manuals = result.scalars().all()

        return list(manuals), total

    async def get_step(self, manual_uuid: UUID, step_number: int) -> Optional[ManualStep]:
        """Get a specific step from a manual."""
        result = await self.db.execute(
            select(ManualStep)
            .where(
                ManualStep.manual_uuid == manual_uuid,
                ManualStep.step_number == step_number
            )
        )
        return result.scalar_one_or_none()

    async def delete_manual(self, manual_id: str) -> bool:
        """Delete a manual by its external ID."""
        manual = await self.get_manual_by_id(manual_id)
        await self.db.delete(manual)
        await self.db.commit()
        logger.info(f"Deleted manual '{manual_id}'")
        return True

    def to_response(self, manual: Manual) -> ManualResponse:
        """Convert manual model to response schema."""
        steps = [
            ManualStepResponse(
                id=step.id,
                step_number=step.step_number,
                title=step.title,
                content=step.content,
                created_at=step.created_at,
            )
            for step in sorted(manual.steps, key=lambda s: s.step_number)
        ]

        return ManualResponse(
            id=manual.id,
            manual_id=manual.manual_id,
            title=manual.title,
            total_steps=manual.total_steps,
            steps=steps,
            created_at=manual.created_at,
            updated_at=manual.updated_at,
        )
