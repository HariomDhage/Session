"""Tests for message endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_message(client: AsyncClient, sample_manual, sample_session, sample_message):
    """Test adding a message to a session."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Add message
    response = await client.post(
        f"/api/v1/sessions/{sample_session['session_id']}/messages",
        json=sample_message
    )
    assert response.status_code == 201

    data = response.json()
    assert data["message"] == sample_message["message"]
    assert data["sender"] == sample_message["sender"]
    assert data["session_id"] == sample_session["session_id"]
    assert data["step_at_time"] == 1


@pytest.mark.asyncio
async def test_add_message_to_nonexistent_session(client: AsyncClient, sample_message):
    """Test adding a message to a non-existent session fails."""
    response = await client.post(
        "/api/v1/sessions/non-existent/messages",
        json=sample_message
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_message_to_ended_session(client: AsyncClient, sample_manual, sample_session, sample_message):
    """Test adding a message to an ended session fails."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # End the session
    await client.patch(
        f"/api/v1/sessions/{sample_session['session_id']}",
        json={"status": "completed"}
    )

    # Try to add message
    response = await client.post(
        f"/api/v1/sessions/{sample_session['session_id']}/messages",
        json=sample_message
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_messages(client: AsyncClient, sample_manual, sample_session, sample_message):
    """Test getting messages from a session."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Add multiple messages
    await client.post(
        f"/api/v1/sessions/{sample_session['session_id']}/messages",
        json=sample_message
    )
    await client.post(
        f"/api/v1/sessions/{sample_session['session_id']}/messages",
        json={**sample_message, "message": "Second message", "sender": "agent"}
    )

    # Get messages
    response = await client.get(f"/api/v1/sessions/{sample_session['session_id']}/messages")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["messages"]) == 2
    assert data["session_id"] == sample_session["session_id"]


@pytest.mark.asyncio
async def test_get_messages_pagination(client: AsyncClient, sample_manual, sample_session, sample_message):
    """Test message pagination."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Add 5 messages
    for i in range(5):
        await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/messages",
            json={**sample_message, "message": f"Message {i+1}"}
        )

    # Get first 2 messages
    response = await client.get(
        f"/api/v1/sessions/{sample_session['session_id']}/messages?limit=2"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 5
    assert len(data["messages"]) == 2
