"""Rate limiting middleware for API protection."""
import os
import time
import logging
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Disable rate limiting during tests
RATE_LIMIT_DISABLED = os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true"


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please slow down.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm.

    For production, replace with Redis-based implementation.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests: dict[str, list[float]] = defaultdict(list)
        self.hour_requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup_old_requests(self, requests: list[float], window_seconds: int) -> list[float]:
        """Remove requests older than the window."""
        cutoff = time.time() - window_seconds
        return [req for req in requests if req > cutoff]

    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """
        Check if request is allowed for the client.

        Returns:
            tuple: (is_allowed, retry_after_seconds)
        """
        current_time = time.time()

        # Clean up old requests
        self.minute_requests[client_id] = self._cleanup_old_requests(
            self.minute_requests[client_id], 60
        )
        self.hour_requests[client_id] = self._cleanup_old_requests(
            self.hour_requests[client_id], 3600
        )

        # Check minute limit
        if len(self.minute_requests[client_id]) >= self.requests_per_minute:
            oldest = min(self.minute_requests[client_id])
            retry_after = int(60 - (current_time - oldest)) + 1
            return False, retry_after

        # Check hour limit
        if len(self.hour_requests[client_id]) >= self.requests_per_hour:
            oldest = min(self.hour_requests[client_id])
            retry_after = int(3600 - (current_time - oldest)) + 1
            return False, retry_after

        # Record the request
        self.minute_requests[client_id].append(current_time)
        self.hour_requests[client_id].append(current_time)

        return True, 0

    def get_remaining(self, client_id: str) -> dict:
        """Get remaining request counts for a client."""
        # Clean up first
        self.minute_requests[client_id] = self._cleanup_old_requests(
            self.minute_requests[client_id], 60
        )
        self.hour_requests[client_id] = self._cleanup_old_requests(
            self.hour_requests[client_id], 3600
        )

        return {
            "minute": {
                "limit": self.requests_per_minute,
                "remaining": self.requests_per_minute - len(self.minute_requests[client_id]),
                "reset_seconds": 60,
            },
            "hour": {
                "limit": self.requests_per_hour,
                "remaining": self.requests_per_hour - len(self.hour_requests[client_id]),
                "reset_seconds": 3600,
            },
        }


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter(
    requests_per_minute=100,  # 100 requests per minute
    requests_per_hour=2000,   # 2000 requests per hour
)


def get_client_id(request: Request) -> str:
    """Extract client identifier from request."""
    # Try X-Forwarded-For header first (for proxied requests)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Try X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to client host
    if request.client:
        return request.client.host

    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting on API requests."""

    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting if disabled (for testing)
        if RATE_LIMIT_DISABLED:
            return await call_next(request)

        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        client_id = get_client_id(request)
        is_allowed, retry_after = rate_limiter.is_allowed(client_id)

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            raise RateLimitExceeded(retry_after=retry_after)

        # Get remaining limits
        remaining = rate_limiter.get_remaining(client_id)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(remaining["minute"]["limit"])
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute"]["remaining"])
        response.headers["X-RateLimit-Limit-Hour"] = str(remaining["hour"]["limit"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour"]["remaining"])

        return response
