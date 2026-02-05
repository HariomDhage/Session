"""Progress service for step tracking with edge case handling."""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session, ProgressEvent, ManualStep
from app.schemas.progress import (
    ProgressUpdate,
    ProgressResponse,
    NextStepResponse,
    NextStepInfo,
    StepStatus,
)
from app.services.session_service import SessionService
from app.services.manual_service import ManualService
from app.services.feedback_service import FeedbackService
from app.utils.exceptions import (
    InvalidStepError,
    DuplicateProgressUpdateError,
    OutOfOrderUpdateError,
    SessionEndedError,
)

logger = logging.getLogger(__name__)


class ProgressService:
    """Service for progress tracking operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = SessionService(db)
        self.manual_service = ManualService(db)
        self.feedback_service = FeedbackService()

    async def update_progress(
        self,
        session_id: str,
        progress_data: ProgressUpdate
    ) -> ProgressResponse:
        """
        Process a progress update for a session.

        Handles:
        - Invalid step numbers
        - Duplicate updates (via idempotency key)
        - Out-of-order updates
        - Session already ended
        - Concurrent updates (via row locking)
        """
        # Get session with lock to prevent concurrent updates
        session = await self.session_service.get_session_with_lock(session_id)

        # Edge Case 4: Session Already Ended
        self.session_service.validate_session_active(session)

        # Get manual for validation
        manual = await self.manual_service.get_manual_by_uuid(session.manual_uuid)

        # Edge Case 1: Invalid Step Numbers
        if progress_data.current_step < 1:
            raise InvalidStepError("Step number must be >= 1")
        if progress_data.current_step > manual.total_steps:
            raise InvalidStepError(
                f"Step {progress_data.current_step} exceeds manual's total steps ({manual.total_steps})"
            )

        # Edge Case 2: Duplicate Updates (check idempotency key)
        if progress_data.idempotency_key:
            existing = await self.db.execute(
                select(ProgressEvent).where(
                    ProgressEvent.session_uuid == session.id,
                    ProgressEvent.idempotency_key == progress_data.idempotency_key
                )
            )
            if existing.scalar_one_or_none():
                raise DuplicateProgressUpdateError(progress_data.idempotency_key)

        # Edge Case 3: Out-of-Order Updates
        # Only process if it's the current step or exactly the next step
        if progress_data.current_step < session.current_step:
            logger.warning(
                f"Received update for step {progress_data.current_step} but session "
                f"is already on step {session.current_step}"
            )
            # Allow it but log as warning - this handles replays gracefully

        previous_step = session.current_step
        should_increment = False

        # Only increment if:
        # 1. Status is DONE
        # 2. The current_step matches the session's current step (or is ahead)
        if progress_data.step_status == StepStatus.DONE:
            if progress_data.current_step >= session.current_step:
                should_increment = True

        # Record progress event for audit trail
        progress_event = ProgressEvent(
            session_uuid=session.id,
            step_number=progress_data.current_step,
            step_status=progress_data.step_status.value,
            previous_step=previous_step,
            processed=should_increment,
            idempotency_key=progress_data.idempotency_key,
        )
        self.db.add(progress_event)

        # Update session if incrementing
        if should_increment:
            session.current_step = progress_data.current_step + 1
            session.version += 1

            # Check if session is completed
            if session.current_step > manual.total_steps:
                session.status = "completed"
                session.ended_at = datetime.now(timezone.utc).isoformat()

        # Update activity
        session.last_activity_at = datetime.now(timezone.utc).isoformat()
        session.updated_at = datetime.now(timezone.utc).isoformat()

        await self.db.commit()
        await self.db.refresh(session)

        # Send feedback to external service
        feedback_sent = await self.feedback_service.send_progress_update(
            session=session,
            manual=manual,
            previous_step=previous_step,
            step_status=progress_data.step_status.value,
        )

        # Get next step info if session is still active
        next_step = None
        if session.status == "active" and session.current_step <= manual.total_steps:
            step = await self.manual_service.get_step(manual.id, session.current_step)
            if step:
                next_step = NextStepInfo(
                    step_number=step.step_number,
                    title=step.title,
                    content=step.content,
                )

        # Build response message
        if session.status == "completed":
            message = "Session completed! All steps finished."
        elif should_increment:
            message = f"Step {previous_step} completed. Ready for step {session.current_step}."
        else:
            message = f"Progress recorded for step {progress_data.current_step} (status: {progress_data.step_status.value})."

        logger.info(
            f"Progress update for session '{session_id}': "
            f"step {previous_step} -> {session.current_step} "
            f"(status: {progress_data.step_status.value}, incremented: {should_increment})"
        )

        return ProgressResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            previous_step=previous_step,
            current_step=session.current_step,
            total_steps=manual.total_steps,
            status=session.status,
            next_step=next_step,
            feedback_sent=feedback_sent,
            message=message,
        )

    async def get_next_step(self, session_id: str) -> NextStepResponse:
        """Get the next recommended step for a session."""
        session = await self.session_service.get_session(session_id)
        manual = await self.manual_service.get_manual_by_uuid(session.manual_uuid)

        is_completed = (
            session.current_step > manual.total_steps or
            session.status == "completed"
        )

        next_step = None
        if not is_completed and session.current_step <= manual.total_steps:
            step = await self.manual_service.get_step(manual.id, session.current_step)
            if step:
                next_step = NextStepInfo(
                    step_number=step.step_number,
                    title=step.title,
                    content=step.content,
                )

        if is_completed:
            message = "All steps completed!"
        else:
            message = f"Current step: {session.current_step} of {manual.total_steps}"

        return NextStepResponse(
            session_id=session.session_id,
            current_step=session.current_step,
            total_steps=manual.total_steps,
            is_completed=is_completed,
            next_step=next_step,
            message=message,
        )
