"""Message API routes for conversation storage."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.message import MessageCreate, MessageResponse, MessageListResponse
from app.services.message_service import MessageService
from app.utils.exceptions import SessionServiceException

router = APIRouter()


@router.post(
    "/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a message",
    description="Add a chat message to a session's conversation history (Type A input).",
)
async def add_message(
    session_id: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a message to the session's conversation.

    This handles Type A input from the upstream AI system.

    - **user_id**: Identifier of the user
    - **message**: The message content
    - **sender**: Who sent the message (user, agent, system)

    Example:
    ```json
    {
      "user_id": "user-123",
      "message": "I have completed the first step.",
      "sender": "user"
    }
    ```
    """
    try:
        service = MessageService(db)
        message = await service.add_message(session_id, message_data)
        return service.to_response(message, session_id)
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/{session_id}/messages",
    response_model=MessageListResponse,
    summary="Get conversation history",
    description="Retrieve all messages from a session's conversation.",
)
async def get_messages(
    session_id: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the conversation history for a session.

    Messages are returned in chronological order (oldest first).
    """
    try:
        service = MessageService(db)
        messages, total, session_id = await service.get_messages(
            session_id,
            skip=skip,
            limit=limit
        )
        return MessageListResponse(
            messages=[service.to_response(m, session_id) for m in messages],
            total=total,
            session_id=session_id
        )
    except SessionServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
