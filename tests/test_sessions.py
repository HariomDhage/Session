"""Tests for session endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient, sample_manual, sample_session):
    """Test creating a new session."""
    # First create a manual
    response = await client.post("/api/v1/manuals", json=sample_manual)
    assert response.status_code == 201

    # Then create a session
    response = await client.post("/api/v1/sessions", json=sample_session)
    assert response.status_code == 201

    data = response.json()
    assert data["session_id"] == sample_session["session_id"]
    assert data["user_id"] == sample_session["user_id"]
    assert data["manual_id"] == sample_manual["manual_id"]
    assert data["current_step"] == 1
    assert data["status"] == "active"
    assert data["total_steps"] == 3


@pytest.mark.asyncio
async def test_create_session_duplicate(client: AsyncClient, sample_manual, sample_session):
    """Test creating a duplicate session fails."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Try to create duplicate
    response = await client.post("/api/v1/sessions", json=sample_session)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_session_missing_manual(client: AsyncClient, sample_session):
    """Test creating a session with non-existent manual fails."""
    response = await client.post("/api/v1/sessions", json=sample_session)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_session(client: AsyncClient, sample_manual, sample_session):
    """Test getting a session by ID."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Get session
    response = await client.get(f"/api/v1/sessions/{sample_session['session_id']}")
    assert response.status_code == 200

    data = response.json()
    assert data["session_id"] == sample_session["session_id"]


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient):
    """Test getting a non-existent session."""
    response = await client.get("/api/v1/sessions/non-existent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient, sample_manual, sample_session):
    """Test listing sessions."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # List sessions
    response = await client.get("/api/v1/sessions")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 1
    assert len(data["sessions"]) >= 1


@pytest.mark.asyncio
async def test_list_sessions_filter_by_user(client: AsyncClient, sample_manual, sample_session):
    """Test listing sessions filtered by user ID."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # List sessions for specific user
    response = await client.get(f"/api/v1/sessions?user_id={sample_session['user_id']}")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_update_session_status(client: AsyncClient, sample_manual, sample_session):
    """Test updating session status."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Update status to completed
    response = await client.patch(
        f"/api/v1/sessions/{sample_session['session_id']}",
        json={"status": "completed"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "completed"
    assert data["ended_at"] is not None


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient, sample_manual, sample_session):
    """Test deleting a session."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Delete session
    response = await client.delete(f"/api/v1/sessions/{sample_session['session_id']}")
    assert response.status_code == 200

    # Verify it's gone
    response = await client.get(f"/api/v1/sessions/{sample_session['session_id']}")
    assert response.status_code == 404
