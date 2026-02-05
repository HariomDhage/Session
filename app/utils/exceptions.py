"""Custom exceptions for the Session Service with standardized error codes."""
from enum import Enum
from fastapi import HTTPException, status
from typing import Optional, Any


class ErrorCode(str, Enum):
    """Standardized error codes for the API."""

    # Session errors (1xxx)
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_ALREADY_EXISTS = "SESSION_ALREADY_EXISTS"
    SESSION_ENDED = "SESSION_ENDED"
    SESSION_CONCURRENT_UPDATE = "SESSION_CONCURRENT_UPDATE"

    # Manual errors (2xxx)
    MANUAL_NOT_FOUND = "MANUAL_NOT_FOUND"
    MANUAL_ALREADY_EXISTS = "MANUAL_ALREADY_EXISTS"

    # Progress errors (3xxx)
    INVALID_STEP_NUMBER = "INVALID_STEP_NUMBER"
    DUPLICATE_PROGRESS_UPDATE = "DUPLICATE_PROGRESS_UPDATE"
    OUT_OF_ORDER_UPDATE = "OUT_OF_ORDER_UPDATE"

    # Validation errors (4xxx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"

    # Rate limiting (5xxx)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors (9xxx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"


class SessionServiceException(Exception):
    """Base exception for session service with standardized error format."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to standardized error response dict."""
        response = {
            "error": {
                "code": self.error_code.value,
                "message": self.message,
            }
        }
        if self.details:
            response["error"]["details"] = self.details
        return response


class SessionNotFoundError(SessionServiceException):
    """Raised when a session is not found."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session '{session_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.SESSION_NOT_FOUND,
            details={"session_id": session_id},
        )


class SessionAlreadyExistsError(SessionServiceException):
    """Raised when trying to create a session that already exists."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session '{session_id}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SESSION_ALREADY_EXISTS,
            details={"session_id": session_id},
        )


class SessionEndedError(SessionServiceException):
    """Raised when trying to update an ended session."""

    def __init__(self, session_id: str, session_status: str):
        super().__init__(
            message=f"Session '{session_id}' is already {session_status}. Cannot accept updates.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.SESSION_ENDED,
            details={"session_id": session_id, "current_status": session_status},
        )


class ManualNotFoundError(SessionServiceException):
    """Raised when a manual is not found."""

    def __init__(self, manual_id: str):
        super().__init__(
            message=f"Manual '{manual_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.MANUAL_NOT_FOUND,
            details={"manual_id": manual_id},
        )


class ManualAlreadyExistsError(SessionServiceException):
    """Raised when trying to create a manual that already exists."""

    def __init__(self, manual_id: str):
        super().__init__(
            message=f"Manual '{manual_id}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.MANUAL_ALREADY_EXISTS,
            details={"manual_id": manual_id},
        )


class InvalidStepError(SessionServiceException):
    """Raised when an invalid step number is provided."""

    def __init__(self, message: str, step: Optional[int] = None, total_steps: Optional[int] = None):
        details = {}
        if step is not None:
            details["step"] = step
        if total_steps is not None:
            details["total_steps"] = total_steps

        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.INVALID_STEP_NUMBER,
            details=details if details else None,
        )


class DuplicateProgressUpdateError(SessionServiceException):
    """Raised when a duplicate progress update is detected."""

    def __init__(self, idempotency_key: str):
        super().__init__(
            message=f"Progress update with idempotency key '{idempotency_key}' already processed",
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.DUPLICATE_PROGRESS_UPDATE,
            details={"idempotency_key": idempotency_key},
        )


class ConcurrentUpdateError(SessionServiceException):
    """Raised when a concurrent update conflict is detected."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Concurrent update detected for session '{session_id}'. Please retry.",
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.SESSION_CONCURRENT_UPDATE,
            details={"session_id": session_id, "retry": True},
        )


class OutOfOrderUpdateError(SessionServiceException):
    """Raised when an out-of-order step update is detected."""

    def __init__(self, expected_step: int, received_step: int):
        super().__init__(
            message=f"Out-of-order update: expected step {expected_step}, received step {received_step}",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.OUT_OF_ORDER_UPDATE,
            details={"expected_step": expected_step, "received_step": received_step},
        )


def handle_service_exception(exc: SessionServiceException) -> HTTPException:
    """Convert service exception to HTTP exception."""
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.to_dict()["error"]
    )
