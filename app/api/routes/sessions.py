"""Session API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionUpdate,
    SessionListResponse,
    SessionDeleteResponse,
)
from app.services.session_service import SessionService
from app.services.feedback_service import FeedbackService
from app.utils.exceptions import SessionServiceException

router = APIRouter()


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new session",
    description="Create a new user session for a specific manual.",
)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new session.

    - **session_id**: Unique identifier for the session
    - **user_id**: Identifier of the user
    - **manual_id**: Identifier of the manual to use

    Example:
    ```json
    {
      "session_id": "session-456",
      "user_id": "user-123",
      "manual_id": "manual-abc"
    }
    ```
    """
    try:
        service = SessionService(db)
        session = await service.create_session(session_data)

        # Send webhook notification
        feedback_service = FeedbackService()
        await feedback_service.send_session_created(session, session.manual)

        return service.to_response(session)
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List sessions",
    description="Get a paginated list of sessions with optional filters.",
)
async def list_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, completed, abandoned)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db)
):
    """List sessions with optional filters."""
    service = SessionService(db)
    sessions, total = await service.list_sessions(
        user_id=user_id,
        status=status,
        skip=skip,
        limit=limit
    )
    return SessionListResponse(
        sessions=[service.to_response(s) for s in sessions],
        total=total
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get a session",
    description="Get details of a specific session by its ID.",
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific session by ID."""
    try:
        service = SessionService(db)
        session = await service.get_session(session_id)
        return service.to_response(session)
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Update a session",
    description="Update session status (e.g., mark as completed or abandoned).",
)
async def update_session(
    session_id: str,
    update_data: SessionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a session.

    - **status**: New status (active, completed, abandoned)

    Example:
    ```json
    {
      "status": "completed"
    }
    ```
    """
    try:
        service = SessionService(db)
        session = await service.update_session(session_id, update_data)

        # Send webhook notification if session ended
        if session.status in ["completed", "abandoned"]:
            feedback_service = FeedbackService()
            await feedback_service.send_session_ended(session, session.manual)

        return service.to_response(session)
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete(
    "/{session_id}",
    response_model=SessionDeleteResponse,
    summary="Delete a session",
    description="Delete a session and all associated data (messages, progress events).",
)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a session by ID."""
    try:
        service = SessionService(db)
        await service.delete_session(session_id)
        return SessionDeleteResponse(
            message="Session deleted successfully",
            session_id=session_id
        )
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
