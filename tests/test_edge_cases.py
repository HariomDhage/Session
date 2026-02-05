"""Tests for edge cases as specified in the assignment."""
import pytest
from httpx import AsyncClient


class TestInvalidStepNumbers:
    """Edge Case 1: Invalid Step Numbers"""

    @pytest.mark.asyncio
    async def test_step_exceeds_total(self, client: AsyncClient, sample_manual, sample_session):
        """Test that step number exceeding total steps is rejected."""
        # Create manual (3 steps) and session
        await client.post("/api/v1/manuals", json=sample_manual)
        await client.post("/api/v1/sessions", json=sample_session)

        # Try to update with step 10 (manual only has 3 steps)
        response = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={
                "user_id": "test-user-001",
                "current_step": 10,
                "step_status": "DONE"
            }
        )
        assert response.status_code == 400
        assert "exceeds" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_step_zero(self, client: AsyncClient, sample_manual, sample_session):
        """Test that step 0 is rejected."""
        await client.post("/api/v1/manuals", json=sample_manual)
        await client.post("/api/v1/sessions", json=sample_session)

        response = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={
                "user_id": "test-user-001",
                "current_step": 0,
                "step_status": "DONE"
            }
        )
        # Pydantic validation should catch this
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_negative_step(self, client: AsyncClient, sample_manual, sample_session):
        """Test that negative step is rejected."""
        await client.post("/api/v1/manuals", json=sample_manual)
        await client.post("/api/v1/sessions", json=sample_session)

        response = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={
                "user_id": "test-user-001",
                "current_step": -1,
                "step_status": "DONE"
            }
        )
        assert response.status_code == 422


class TestDuplicateUpdates:
    """Edge Case 2: Duplicate Updates"""

    @pytest.mark.asyncio
    async def test_duplicate_with_idempotency_key(self, client: AsyncClient, sample_manual, sample_session):
        """Test that duplicate updates with same idempotency key are rejected."""
        await client.post("/api/v1/manuals", json=sample_manual)
        await client.post("/api/v1/sessions", json=sample_session)

        idempotency_key = "unique-key-123"

        # First update
        response1 = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={
                "user_id": "test-user-001",
                "current_step": 1,
                "step_status": "DONE",
                "idempotency_key": idempotency_key
            }
        )
        assert response1.status_code == 200

        # Duplicate update with same key
        response2 = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={
                "user_id": "test-user-001",
                "current_step": 1,
                "step_status": "DONE",
                "idempotency_key": idempotency_key
            }
        )
        assert response2.status_code == 409
        assert "already_processed" in response2.json()["detail"]["status"]

    @pytest.mark.asyncio
    async def test_different_idempotency_keys(self, client: AsyncClient, sample_manual, sample_session):
        """Test that different idempotency keys are processed."""
        await client.post("/api/v1/manuals", json=sample_manual)
        await client.post("/api/v1/sessions", json=sample_session)

        # First update
        response1 = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={
                "user_id": "test-user-001",
                "current_step": 1,
                "step_status": "DONE",
                "idempotency_key": "key-1"
            }
        )
        assert response1.status_code == 200

        # Second update with different key
        response2 = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={
                "user_id": "test-user-001",
                "current_step": 2,
                "step_status": "DONE",
                "idempotency_key": "key-2"
            }
        )
        assert response2.status_code == 200


class TestOutOfOrderUpdates:
    """Edge Case 3: Out-of-Order Updates"""

    @pytest.mark.asyncio
    async def test_past_step_update(self, client: AsyncClient, sample_manual, sample_session):
        """Test handling update for a step already passed."""
        await client.post("/api/v1/manuals", json=sample_manual)
        await client.post("/api/v1/sessions", json=sample_session)

        # Complete step 1 and 2
        await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={"user_id": "test-user-001", "current_step": 1, "step_status": "DONE"}
        )
        await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={"user_id": "test-user-001", "current_step": 2, "step_status": "DONE"}
        )

        # Now session is on step 3, try to update step 1 again
        response = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={"user_id": "test-user-001", "current_step": 1, "step_status": "DONE"}
        )
        # Should be accepted but not increment
        assert response.status_code == 200
        data = response.json()
        # Current step should still be 3
        assert data["current_step"] == 3


class TestSessionAlreadyEnded:
    """Edge Case 4: Session Already Ended"""

    @pytest.mark.asyncio
    async def test_update_completed_session(self, client: AsyncClient, sample_manual, sample_session):
        """Test that updates to completed session are rejected."""
        await client.post("/api/v1/manuals", json=sample_manual)
        await client.post("/api/v1/sessions", json=sample_session)

        # Complete the session
        await client.patch(
            f"/api/v1/sessions/{sample_session['session_id']}",
            json={"status": "completed"}
        )

        # Try to send progress update
        response = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={"user_id": "test-user-001", "current_step": 1, "step_status": "DONE"}
        )
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_abandoned_session(self, client: AsyncClient, sample_manual, sample_session):
        """Test that updates to abandoned session are rejected."""
        await client.post("/api/v1/manuals", json=sample_manual)
        await client.post("/api/v1/sessions", json=sample_session)

        # Abandon the session
        await client.patch(
            f"/api/v1/sessions/{sample_session['session_id']}",
            json={"status": "abandoned"}
        )

        # Try to send progress update
        response = await client.post(
            f"/api/v1/sessions/{sample_session['session_id']}/progress",
            json={"user_id": "test-user-001", "current_step": 1, "step_status": "DONE"}
        )
        assert response.status_code == 400


class TestMissingManual:
    """Edge Case 5: Missing Manual"""

    @pytest.mark.asyncio
    async def test_session_with_nonexistent_manual(self, client: AsyncClient, sample_session):
        """Test that creating session with non-existent manual fails."""
        response = await client.post("/api/v1/sessions", json=sample_session)
        assert response.status_code == 404
        assert "manual" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_nonexistent_manual(self, client: AsyncClient):
        """Test that getting non-existent manual returns 404."""
        response = await client.get("/api/v1/manuals/non-existent-manual")
        assert response.status_code == 404


class TestVariableManualSteps:
    """Test handling manuals with different step counts (2 to 100+)."""

    @pytest.mark.asyncio
    async def test_manual_with_2_steps(self, client: AsyncClient, sample_session):
        """Test manual with minimum steps."""
        manual = {
            "manual_id": "manual-2-steps",
            "title": "Short Manual",
            "steps": [
                {"step_number": 1, "title": "Step 1", "content": "Content 1"},
                {"step_number": 2, "title": "Step 2", "content": "Content 2"},
            ]
        }
        await client.post("/api/v1/manuals", json=manual)

        session = {**sample_session, "manual_id": "manual-2-steps"}
        response = await client.post("/api/v1/sessions", json=session)
        assert response.status_code == 201
        assert response.json()["total_steps"] == 2

    @pytest.mark.asyncio
    async def test_manual_with_many_steps(self, client: AsyncClient, sample_session):
        """Test manual with many steps."""
        steps = [
            {"step_number": i, "title": f"Step {i}", "content": f"Content for step {i}"}
            for i in range(1, 51)  # 50 steps
        ]
        manual = {
            "manual_id": "manual-50-steps",
            "title": "Long Manual",
            "steps": steps
        }
        await client.post("/api/v1/manuals", json=manual)

        session = {**sample_session, "manual_id": "manual-50-steps"}
        response = await client.post("/api/v1/sessions", json=session)
        assert response.status_code == 201
        assert response.json()["total_steps"] == 50


class TestSessionDuration:
    """Test session duration tracking."""

    @pytest.mark.asyncio
    async def test_duration_calculation(self, client: AsyncClient, sample_manual, sample_session):
        """Test that session duration is calculated correctly."""
        await client.post("/api/v1/manuals", json=sample_manual)
        await client.post("/api/v1/sessions", json=sample_session)

        # Get session - should have duration
        response = await client.get(f"/api/v1/sessions/{sample_session['session_id']}")
        data = response.json()

        assert "duration_seconds" in data
        assert data["duration_seconds"] is not None
        assert data["duration_seconds"] >= 0
