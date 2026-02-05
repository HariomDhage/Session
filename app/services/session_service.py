"""Session service for business logic."""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Session, Manual
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse, SessionStatus
from app.services.manual_service import ManualService
from app.utils.exceptions import (
    SessionNotFoundError,
    SessionAlreadyExistsError,
    SessionEndedError,
    ManualNotFoundError,
)

logger = logging.getLogger(__name__)


class SessionService:
    """Service for session-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.manual_service = ManualService(db)

    async def create_session(self, session_data: SessionCreate) -> Session:
        """Create a new session."""
        # Check if session_id already exists
        existing = await self.db.execute(
            select(Session).where(Session.session_id == session_data.session_id)
        )
        if existing.scalar_one_or_none():
            raise SessionAlreadyExistsError(session_data.session_id)

        # Verify manual exists
        manual = await self.manual_service.get_manual_by_id(session_data.manual_id)

        # Create session
        session = Session(
            session_id=session_data.session_id,
            user_id=session_data.user_id,
            manual_uuid=manual.id,
            current_step=1,
            status="active",
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        # Eagerly load the manual relationship to avoid lazy loading issues
        result = await self.db.execute(
            select(Session)
            .where(Session.id == session.id)
            .options(selectinload(Session.manual))
        )
        session = result.scalar_one()

        logger.info(
            f"Created session '{session.session_id}' for user '{session.user_id}' "
            f"with manual '{manual.manual_id}'"
        )
        return session

    async def get_session(self, session_id: str) -> Session:
        """Get a session by its external ID."""
        result = await self.db.execute(
            select(Session)
            .where(Session.session_id == session_id)
            .options(selectinload(Session.manual))
        )
        session = result.scalar_one_or_none()

        if not session:
            raise SessionNotFoundError(session_id)

        return session

    async def get_session_with_lock(self, session_id: str) -> Session:
        """Get a session with row-level lock for updates."""
        result = await self.db.execute(
            select(Session)
            .where(Session.session_id == session_id)
            .options(selectinload(Session.manual))
            .with_for_update()
        )
        session = result.scalar_one_or_none()

        if not session:
            raise SessionNotFoundError(session_id)

        return session

    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Session], int]:
        """List sessions with optional filters."""
        query = select(Session).options(selectinload(Session.manual))

        if user_id:
            query = query.where(Session.user_id == user_id)
        if status:
            query = query.where(Session.status == status)

        # Get total count
        count_query = select(Session)
        if user_id:
            count_query = count_query.where(Session.user_id == user_id)
        if status:
            count_query = count_query.where(Session.status == status)
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Get paginated results
        result = await self.db.execute(
            query.offset(skip).limit(limit).order_by(Session.created_at.desc())
        )
        sessions = result.scalars().all()

        return list(sessions), total

    async def update_session(
        self,
        session_id: str,
        update_data: SessionUpdate
    ) -> Session:
        """Update a session."""
        session = await self.get_session(session_id)

        if update_data.status:
            # Check if trying to reactivate an ended session
            if session.status != "active" and update_data.status == SessionStatus.ACTIVE:
                raise SessionEndedError(session_id, session.status)

            session.status = update_data.status.value

            # Set ended_at if completing or abandoning
            if update_data.status in [SessionStatus.COMPLETED, SessionStatus.ABANDONED]:
                session.ended_at = datetime.now(timezone.utc).isoformat()

        session.updated_at = datetime.now(timezone.utc).isoformat()
        await self.db.commit()

        # Reload with relationship to avoid lazy loading
        result = await self.db.execute(
            select(Session)
            .where(Session.id == session.id)
            .options(selectinload(Session.manual))
        )
        session = result.scalar_one()

        logger.info(f"Updated session '{session_id}' status to '{session.status}'")
        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session = await self.get_session(session_id)
        await self.db.delete(session)
        await self.db.commit()
        logger.info(f"Deleted session '{session_id}'")
        return True

    async def update_activity(self, session: Session) -> None:
        """Update last activity timestamp."""
        session.last_activity_at = datetime.now(timezone.utc).isoformat()
        session.updated_at = datetime.now(timezone.utc).isoformat()
        await self.db.commit()

    def validate_session_active(self, session: Session) -> None:
        """Validate that a session is still active."""
        if session.status != "active":
            raise SessionEndedError(session.session_id, session.status)

    def to_response(self, session: Session) -> SessionResponse:
        """Convert session model to response schema."""
        return SessionResponse(
            id=session.id,
            session_id=session.session_id,
            user_id=session.user_id,
            manual_id=session.manual.manual_id,
            current_step=session.current_step,
            total_steps=session.manual.total_steps,
            status=session.status,
            started_at=session.started_at,
            ended_at=session.ended_at,
            last_activity_at=session.last_activity_at,
            duration_seconds=session.duration_seconds,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
