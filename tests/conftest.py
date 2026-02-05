"""Test fixtures and configuration."""
import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.database import Base, get_db
from app.api.deps import get_db as api_get_db

# Use PostgreSQL for testing (same as the running container)
# Falls back to container's default if not set
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/sessions"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up data after each test (but keep tables)
    async with engine.begin() as conn:
        # Delete data in reverse order of foreign key dependencies
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_session) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database override."""

    async def override_get_db():
        yield test_session

    app.dependency_overrides[api_get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_manual():
    """Sample manual data for testing."""
    return {
        "manual_id": "test-manual-001",
        "title": "Test Manual",
        "steps": [
            {"step_number": 1, "title": "Step 1", "content": "Content for step 1"},
            {"step_number": 2, "title": "Step 2", "content": "Content for step 2"},
            {"step_number": 3, "title": "Step 3", "content": "Content for step 3"},
        ]
    }


@pytest.fixture
def sample_session():
    """Sample session data for testing."""
    return {
        "session_id": "test-session-001",
        "user_id": "test-user-001",
        "manual_id": "test-manual-001"
    }


@pytest.fixture
def sample_message():
    """Sample message data for testing."""
    return {
        "user_id": "test-user-001",
        "message": "I have completed this step.",
        "sender": "user"
    }


@pytest.fixture
def sample_progress():
    """Sample progress update data for testing."""
    return {
        "user_id": "test-user-001",
        "current_step": 1,
        "step_status": "DONE"
    }
