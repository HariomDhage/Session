"""Progress API routes for step tracking."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.progress import (
    ProgressUpdate,
    ProgressResponse,
    NextStepResponse,
    DuplicateProgressResponse,
)
from app.services.progress_service import ProgressService
from app.utils.exceptions import SessionServiceException, DuplicateProgressUpdateError

router = APIRouter()


@router.post(
    "/{session_id}/progress",
    response_model=ProgressResponse,
    summary="Submit progress update",
    description="Submit a progress update for a session (Type B & C input). "
                "DONE status increments the step counter, ONGOING does not.",
    responses={
        200: {"description": "Progress updated successfully"},
        400: {"description": "Invalid step number or session ended"},
        404: {"description": "Session not found"},
        409: {"description": "Duplicate update (if idempotency_key provided)"},
    }
)
async def update_progress(
    session_id: str,
    progress_data: ProgressUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a progress update for a session.

    This handles Type B & C input from the upstream AI system.

    **Step Status:**
    - **DONE**: User finished this step, increment the counter
    - **ONGOING**: User is still working on it, don't increment

    **Edge Cases Handled:**
    - Invalid step numbers (rejected with 400)
    - Duplicate updates (rejected with 409 if idempotency_key matches)
    - Out-of-order updates (logged but allowed)
    - Session already ended (rejected with 400)
    - Concurrent updates (handled with row-level locking)

    Example:
    ```json
    {
      "user_id": "user-123",
      "current_step": 2,
      "step_status": "DONE",
      "idempotency_key": "progress-uuid-123"
    }
    ```
    """
    try:
        service = ProgressService(db)
        return await service.update_progress(session_id, progress_data)
    except DuplicateProgressUpdateError as e:
        # Return 409 Conflict for duplicates
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "already_processed",
                "message": e.message,
                "session_id": session_id,
                "idempotency_key": progress_data.idempotency_key,
            }
        )
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/{session_id}/next-step",
    response_model=NextStepResponse,
    summary="Get next recommended step",
    description="Get the next step the user should work on.",
)
async def get_next_step(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the next recommended step for a session.

    Returns the current step information including title and content,
    or indicates if the session is completed.
    """
    try:
        service = ProgressService(db)
        return await service.get_next_step(session_id)
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
