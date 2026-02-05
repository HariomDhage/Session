"""FastAPI application entry point."""
import logging
import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware

from sqlalchemy import text

from app.config import get_settings
from app.database import init_db, close_db, async_session_maker
from app.api.routes import api_router
from app.utils.exceptions import SessionServiceException
from app.services.background_tasks import background_service
from app.middleware.rate_limiter import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Session Service...")
    await init_db()
    logger.info("Database initialized")

    # Start background tasks
    background_task = asyncio.create_task(background_service.start())
    logger.info("Background task service started")

    yield

    # Shutdown
    logger.info("Shutting down Session Service...")
    background_service.stop()
    background_task.cancel()
    try:
        await background_task
    except asyncio.CancelledError:
        pass
    logger.info("Background task service stopped")

    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Session Service API

A backend service for tracking user sessions with an AI agent.

### Features
- **Session Management**: Create, retrieve, update, and delete sessions
- **Progress Tracking**: Track user progress through instructional steps
- **Conversation Storage**: Store and retrieve chat history
- **Feedback Mechanism**: Send updates to external instruction delivery service

### Input Types
The service accepts two types of input from upstream:

**Type A - Chat Messages:**
```json
{
  "user_id": "user-123",
  "message": "I have completed the first step.",
  "sender": "user"
}
```

**Type B & C - Progress Updates:**
```json
{
  "user_id": "user-123",
  "current_step": 2,
  "step_status": "DONE"
}
```

### Edge Cases Handled
- Invalid step numbers
- Duplicate updates (via idempotency key)
- Out-of-order updates
- Session already ended
- Missing manual
- Concurrent updates

    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)


# Global exception handler for service exceptions
@app.exception_handler(SessionServiceException)
async def service_exception_handler(request: Request, exc: SessionServiceException):
    """Handle service-level exceptions with standardized error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Request ID middleware for tracing
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint with database connectivity verification.

    Returns service status and database connection health.
    """
    db_healthy = False
    db_error = None

    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
            db_healthy = True
    except Exception as e:
        db_error = str(e)

    # Get background service stats
    bg_stats = await background_service.get_stats()

    status_value = "healthy" if db_healthy else "degraded"

    return {
        "status": status_value,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": {
            "database": {
                "healthy": db_healthy,
                "error": db_error,
            },
            "background_tasks": bg_stats,
        }
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }


def custom_openapi():
    """Custom OpenAPI schema with examples."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=app.description,
        routes=app.routes,
    )

    # Add example responses
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
