"""Message service for conversation storage."""
import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConversationMessage, Session
from app.schemas.message import MessageCreate, MessageResponse
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)


class MessageService:
    """Service for message-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = SessionService(db)

    async def add_message(
        self,
        session_id: str,
        message_data: MessageCreate
    ) -> ConversationMessage:
        """Add a message to a session's conversation."""
        # Get session and validate it's active
        session = await self.session_service.get_session(session_id)
        self.session_service.validate_session_active(session)

        # Create message
        message = ConversationMessage(
            session_uuid=session.id,
            message_text=message_data.message,
            sender=message_data.sender.value,
            step_at_time=session.current_step,
        )
        self.db.add(message)

        # Update session activity
        await self.session_service.update_activity(session)

        await self.db.commit()
        await self.db.refresh(message)

        logger.info(
            f"Added message from '{message_data.sender.value}' to session '{session_id}' "
            f"at step {session.current_step}"
        )
        return message

    async def get_messages(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[ConversationMessage], int, str]:
        """Get all messages for a session."""
        # Verify session exists
        session = await self.session_service.get_session(session_id)

        # Get total count
        count_result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_uuid == session.id)
        )
        total = len(count_result.scalars().all())

        # Get paginated messages
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_uuid == session.id)
            .order_by(ConversationMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        messages = result.scalars().all()

        return list(messages), total, session.session_id

    def to_response(
        self,
        message: ConversationMessage,
        session_id: str
    ) -> MessageResponse:
        """Convert message model to response schema."""
        return MessageResponse(
            id=message.id,
            session_id=session_id,
            message=message.message_text,
            sender=message.sender,
            step_at_time=message.step_at_time,
            created_at=message.created_at,
        )
