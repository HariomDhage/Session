"""Tests for progress endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_progress_update_done(client: AsyncClient, sample_manual, sample_session, sample_progress):
    """Test progress update with DONE status increments step."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Submit progress update
    response = await client.post(
        f"/api/v1/sessions/{sample_session['session_id']}/progress",
        json=sample_progress
    )
    assert response.status_code == 200

    data = response.json()
    assert data["previous_step"] == 1
    assert data["current_step"] == 2  # Incremented
    assert data["status"] == "active"
    assert data["next_step"] is not None
    assert data["next_step"]["step_number"] == 2


@pytest.mark.asyncio
async def test_progress_update_ongoing(client: AsyncClient, sample_manual, sample_session):
    """Test progress update with ONGOING status does not increment step."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Submit progress update with ONGOING
    response = await client.post(
        f"/api/v1/sessions/{sample_session['session_id']}/progress",
        json={
            "user_id": "test-user-001",
            "current_step": 1,
            "step_status": "ONGOING"
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert data["previous_step"] == 1
    assert data["current_step"] == 1  # Not incremented


@pytest.mark.asyncio
async def test_progress_update_completes_session(client: AsyncClient, sample_manual, sample_session):
    """Test completing all steps ends the session."""
    # Create manual and session (3 steps)
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Complete all steps
    for step in [1, 2, 3]:
        response = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={
                "user_id": "test-user-001",
                "current_step": step,
                "step_status": "DONE"
            }
        )

    # After step 3, session should be completed
    data = response.json()
    assert data["status"] == "completed"
    assert data["current_step"] == 4  # Past last step


@pytest.mark.asyncio
async def test_get_next_step(client: AsyncClient, sample_manual, sample_session):
    """Test getting next step recommendation."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Get next step
    response = await client.get(
        f"/api/v1/sessions/{sample_session['session_id']}/next-step"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["current_step"] == 1
    assert data["total_steps"] == 3
    assert data["is_completed"] is False
    assert data["next_step"]["step_number"] == 1
    assert data["next_step"]["title"] == "Step 1"


@pytest.mark.asyncio
async def test_get_next_step_completed_session(client: AsyncClient, sample_manual, sample_session):
    """Test getting next step for completed session."""
    # Create manual and session
    await client.post("/api/v1/manuals", json=sample_manual)
    await client.post("/api/v1/sessions", json=sample_session)

    # Complete all steps
    for step in [1, 2, 3]:
        await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={
                "user_id": "test-user-001",
                "current_step": step,
                "step_status": "DONE"
            }
        )

    # Get next step
    response = await client.get(
        f"/api/v1/sessions/{sample_session['session_id']}/next-step"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["is_completed"] is True
    assert data["next_step"] is None
