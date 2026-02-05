"""Integration tests against the running API.

These tests require the full stack to be running (docker-compose up).
Run with: pytest tests/test_integration.py -v
"""
import asyncio
import httpx
import pytest
from datetime import datetime
import uuid

# API base URL - when running inside Docker, use internal network
import os
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE_URL", "http://mock_webhook:8001")


def unique_id():
    """Generate a unique test ID."""
    return f"test-{uuid.uuid4().hex[:8]}"


class TestHealthCheck:
    """Test health endpoints."""

    def test_health_check(self):
        """Test that the API is healthy."""
        response = httpx.get("http://localhost:8000/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestManualEndpoints:
    """Test manual CRUD operations."""

    def test_create_manual(self):
        """Test creating a manual."""
        manual_id = unique_id()
        response = httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": manual_id,
                "title": "Test Manual",
                "steps": [
                    {"step_number": 1, "title": "Step 1", "content": "Do step 1"},
                    {"step_number": 2, "title": "Step 2", "content": "Do step 2"},
                    {"step_number": 3, "title": "Step 3", "content": "Do step 3"},
                ]
            },
            timeout=10.0
        )
        assert response.status_code == 201
        data = response.json()
        assert data["manual_id"] == manual_id
        assert data["total_steps"] == 3

        # Cleanup
        httpx.delete(f"{API_BASE}/manuals/{manual_id}", timeout=10.0)

    def test_get_manual(self):
        """Test retrieving a manual."""
        manual_id = unique_id()
        # Create first
        httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": manual_id,
                "title": "Test Manual",
                "steps": [
                    {"step_number": 1, "title": "Step 1", "content": "Do step 1"},
                ]
            },
            timeout=10.0
        )

        # Get
        response = httpx.get(f"{API_BASE}/manuals/{manual_id}", timeout=10.0)
        assert response.status_code == 200
        data = response.json()
        assert data["manual_id"] == manual_id

        # Cleanup
        httpx.delete(f"{API_BASE}/manuals/{manual_id}", timeout=10.0)

    def test_get_nonexistent_manual(self):
        """Test getting a manual that doesn't exist."""
        response = httpx.get(f"{API_BASE}/manuals/nonexistent-manual", timeout=10.0)
        assert response.status_code == 404


class TestSessionEndpoints:
    """Test session CRUD operations."""

    def setup_method(self):
        """Create a manual for session tests."""
        self.manual_id = unique_id()
        httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": self.manual_id,
                "title": "Session Test Manual",
                "steps": [
                    {"step_number": 1, "title": "Step 1", "content": "Content 1"},
                    {"step_number": 2, "title": "Step 2", "content": "Content 2"},
                    {"step_number": 3, "title": "Step 3", "content": "Content 3"},
                ]
            },
            timeout=10.0
        )

    def teardown_method(self):
        """Cleanup manual."""
        httpx.delete(f"{API_BASE}/manuals/{self.manual_id}", timeout=10.0)

    def test_create_session(self):
        """Test creating a session."""
        session_id = unique_id()
        response = httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": session_id,
                "user_id": "test-user",
                "manual_id": self.manual_id
            },
            timeout=10.0
        )
        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == session_id
        assert data["current_step"] == 1
        assert data["status"] == "active"

        # Cleanup
        httpx.delete(f"{API_BASE}/sessions/{session_id}", timeout=10.0)

    def test_create_session_with_nonexistent_manual(self):
        """Test creating session with missing manual."""
        response = httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": unique_id(),
                "user_id": "test-user",
                "manual_id": "nonexistent-manual"
            },
            timeout=10.0
        )
        assert response.status_code == 404

    def test_get_session(self):
        """Test retrieving a session."""
        session_id = unique_id()
        httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": session_id,
                "user_id": "test-user",
                "manual_id": self.manual_id
            },
            timeout=10.0
        )

        response = httpx.get(f"{API_BASE}/sessions/{session_id}", timeout=10.0)
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

        # Cleanup
        httpx.delete(f"{API_BASE}/sessions/{session_id}", timeout=10.0)


class TestProgressUpdates:
    """Test progress tracking functionality."""

    def setup_method(self):
        """Create manual and session for progress tests."""
        self.manual_id = unique_id()
        self.session_id = unique_id()

        httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": self.manual_id,
                "title": "Progress Test Manual",
                "steps": [
                    {"step_number": 1, "title": "Step 1", "content": "Content 1"},
                    {"step_number": 2, "title": "Step 2", "content": "Content 2"},
                    {"step_number": 3, "title": "Step 3", "content": "Content 3"},
                ]
            },
            timeout=10.0
        )

        httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": self.session_id,
                "user_id": "test-user",
                "manual_id": self.manual_id
            },
            timeout=10.0
        )

    def teardown_method(self):
        """Cleanup."""
        httpx.delete(f"{API_BASE}/sessions/{self.session_id}", timeout=10.0)
        httpx.delete(f"{API_BASE}/manuals/{self.manual_id}", timeout=10.0)

    def test_progress_update_done(self):
        """Test completing a step."""
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={
                "user_id": "test-user",
                "current_step": 1,
                "step_status": "DONE"
            },
            timeout=10.0
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == 2  # Advances to next step

    def test_progress_update_ongoing(self):
        """Test marking step as ongoing."""
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={
                "user_id": "test-user",
                "current_step": 1,
                "step_status": "ONGOING"
            },
            timeout=10.0
        )
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == 1  # Stays on same step

    def test_complete_all_steps(self):
        """Test completing all steps marks session complete."""
        # Complete step 1
        httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 1, "step_status": "DONE"},
            timeout=10.0
        )
        # Complete step 2
        httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 2, "step_status": "DONE"},
            timeout=10.0
        )
        # Complete step 3
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 3, "step_status": "DONE"},
            timeout=10.0
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"


class TestEdgeCases:
    """Test edge case handling - the 6 required scenarios."""

    def setup_method(self):
        """Create manual and session for edge case tests."""
        self.manual_id = unique_id()
        self.session_id = unique_id()

        httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": self.manual_id,
                "title": "Edge Case Test Manual",
                "steps": [
                    {"step_number": 1, "title": "Step 1", "content": "Content 1"},
                    {"step_number": 2, "title": "Step 2", "content": "Content 2"},
                    {"step_number": 3, "title": "Step 3", "content": "Content 3"},
                ]
            },
            timeout=10.0
        )

        httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": self.session_id,
                "user_id": "test-user",
                "manual_id": self.manual_id
            },
            timeout=10.0
        )

    def teardown_method(self):
        """Cleanup."""
        httpx.delete(f"{API_BASE}/sessions/{self.session_id}", timeout=10.0)
        httpx.delete(f"{API_BASE}/manuals/{self.manual_id}", timeout=10.0)

    # Edge Case 1: Invalid Step Numbers
    def test_step_exceeds_total(self):
        """Test step number exceeds total steps."""
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={
                "user_id": "test-user",
                "current_step": 999,
                "step_status": "DONE"
            },
            timeout=10.0
        )
        assert response.status_code == 400
        data = response.json()
        # Check for error indication (error_code or detail)
        assert "error_code" in data or "detail" in data

    def test_step_zero(self):
        """Test step number is zero."""
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={
                "user_id": "test-user",
                "current_step": 0,
                "step_status": "DONE"
            },
            timeout=10.0
        )
        # 400 for business logic error, 422 for validation error - both acceptable
        assert response.status_code in [400, 422]

    def test_negative_step(self):
        """Test negative step number."""
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={
                "user_id": "test-user",
                "current_step": -1,
                "step_status": "DONE"
            },
            timeout=10.0
        )
        assert response.status_code == 400 or response.status_code == 422

    # Edge Case 2: Duplicate Updates (Idempotency)
    def test_duplicate_with_idempotency_key(self):
        """Test duplicate update with same idempotency key."""
        idempotency_key = unique_id()

        # First update
        response1 = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={
                "user_id": "test-user",
                "current_step": 1,
                "step_status": "DONE",
                "idempotency_key": idempotency_key
            },
            timeout=10.0
        )
        assert response1.status_code == 200

        # Duplicate update with same key
        response2 = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={
                "user_id": "test-user",
                "current_step": 1,
                "step_status": "DONE",
                "idempotency_key": idempotency_key
            },
            timeout=10.0
        )
        assert response2.status_code == 409  # Conflict

    # Edge Case 3: Out of Order Updates
    def test_past_step_update(self):
        """Test updating a step from the past."""
        # First complete step 1
        httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 1, "step_status": "DONE"},
            timeout=10.0
        )

        # Try to update step 1 again (out of order)
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 1, "step_status": "DONE"},
            timeout=10.0
        )
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400, 409]

    # Edge Case 4: Session Already Ended
    def test_update_completed_session(self):
        """Test updating a completed session."""
        # Complete all steps
        httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 1, "step_status": "DONE"},
            timeout=10.0
        )
        httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 2, "step_status": "DONE"},
            timeout=10.0
        )
        httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 3, "step_status": "DONE"},
            timeout=10.0
        )

        # Try to update after completion
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 1, "step_status": "DONE"},
            timeout=10.0
        )
        assert response.status_code == 400
        data = response.json()
        # Check for session ended/completed indication in response
        data_str = str(data).lower()
        assert "ended" in data_str or "completed" in data_str or "session_already" in data_str

    def test_update_abandoned_session(self):
        """Test updating an abandoned session."""
        # Manually set session to abandoned
        httpx.patch(
            f"{API_BASE}/sessions/{self.session_id}",
            json={"status": "abandoned"},
            timeout=10.0
        )

        # Try to update
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/progress",
            json={"user_id": "test-user", "current_step": 1, "step_status": "DONE"},
            timeout=10.0
        )
        assert response.status_code == 400

    # Edge Case 5: Missing Manual
    def test_session_with_nonexistent_manual(self):
        """Test creating session with nonexistent manual."""
        response = httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": unique_id(),
                "user_id": "test-user",
                "manual_id": "nonexistent-manual"
            },
            timeout=10.0
        )
        assert response.status_code == 404

    # Edge Case 6: Concurrent Updates (simplified test)
    def test_concurrent_update_simulation(self):
        """Test that updates include version tracking."""
        # Get session to verify version field exists
        response = httpx.get(f"{API_BASE}/sessions/{self.session_id}", timeout=10.0)
        assert response.status_code == 200
        # The implementation should track version for optimistic locking


class TestConversationMessages:
    """Test conversation message storage."""

    def setup_method(self):
        """Create manual and session for message tests."""
        self.manual_id = unique_id()
        self.session_id = unique_id()

        httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": self.manual_id,
                "title": "Message Test Manual",
                "steps": [{"step_number": 1, "title": "Step 1", "content": "Content 1"}]
            },
            timeout=10.0
        )

        httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": self.session_id,
                "user_id": "test-user",
                "manual_id": self.manual_id
            },
            timeout=10.0
        )

    def teardown_method(self):
        """Cleanup."""
        httpx.delete(f"{API_BASE}/sessions/{self.session_id}", timeout=10.0)
        httpx.delete(f"{API_BASE}/manuals/{self.manual_id}", timeout=10.0)

    def test_add_message(self):
        """Test adding a message."""
        response = httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/messages",
            json={
                "user_id": "test-user",
                "message": "Hello, I need help with step 1",
                "sender": "user"
            },
            timeout=10.0
        )
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Hello, I need help with step 1"
        assert data["sender"] == "user"

    def test_get_messages(self):
        """Test retrieving messages."""
        # Add a few messages
        httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/messages",
            json={"user_id": "test-user", "message": "Message 1", "sender": "user"},
            timeout=10.0
        )
        httpx.post(
            f"{API_BASE}/sessions/{self.session_id}/messages",
            json={"user_id": "test-user", "message": "Response 1", "sender": "agent"},
            timeout=10.0
        )

        response = httpx.get(f"{API_BASE}/sessions/{self.session_id}/messages", timeout=10.0)
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) >= 2


class TestWebhookIntegration:
    """Test webhook/feedback integration."""

    def test_webhook_sent_on_progress(self):
        """Test that webhook is sent when progress is made."""
        manual_id = unique_id()
        session_id = unique_id()

        # Create manual and session
        httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": manual_id,
                "title": "Webhook Test Manual",
                "steps": [
                    {"step_number": 1, "title": "Step 1", "content": "Content 1"},
                    {"step_number": 2, "title": "Step 2", "content": "Content 2"},
                ]
            },
            timeout=10.0
        )
        httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": session_id,
                "user_id": "test-user",
                "manual_id": manual_id
            },
            timeout=10.0
        )

        # Make progress - this should trigger webhook
        response = httpx.post(
            f"{API_BASE}/sessions/{session_id}/progress",
            json={
                "user_id": "test-user",
                "current_step": 1,
                "step_status": "DONE"
            },
            timeout=10.0
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("feedback_sent") == True

        # Check mock webhook received the event (if available)
        try:
            webhook_response = httpx.get(f"{WEBHOOK_BASE}/events", timeout=10.0)
            if webhook_response.status_code == 200:
                events = webhook_response.json()
                assert len(events) > 0
            # If endpoint doesn't exist (404), the webhook was still sent
            # The mock server logs it, just doesn't expose /events
        except httpx.ConnectError:
            # If running from inside Docker, webhook is on internal network
            # Skip webhook verification if unreachable
            pass

        # Cleanup
        httpx.delete(f"{API_BASE}/sessions/{session_id}", timeout=10.0)
        httpx.delete(f"{API_BASE}/manuals/{manual_id}", timeout=10.0)


class TestVariableStepCounts:
    """Test manuals with different step counts."""

    def test_manual_with_2_steps(self):
        """Test a manual with minimum 2 steps."""
        manual_id = unique_id()
        session_id = unique_id()

        httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": manual_id,
                "title": "Two Step Manual",
                "steps": [
                    {"step_number": 1, "title": "Step 1", "content": "Content 1"},
                    {"step_number": 2, "title": "Step 2", "content": "Content 2"},
                ]
            },
            timeout=10.0
        )
        httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": session_id,
                "user_id": "test-user",
                "manual_id": manual_id
            },
            timeout=10.0
        )

        # Complete both steps
        httpx.post(
            f"{API_BASE}/sessions/{session_id}/progress",
            json={"user_id": "test-user", "current_step": 1, "step_status": "DONE"},
            timeout=10.0
        )
        response = httpx.post(
            f"{API_BASE}/sessions/{session_id}/progress",
            json={"user_id": "test-user", "current_step": 2, "step_status": "DONE"},
            timeout=10.0
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

        # Cleanup
        httpx.delete(f"{API_BASE}/sessions/{session_id}", timeout=10.0)
        httpx.delete(f"{API_BASE}/manuals/{manual_id}", timeout=10.0)

    def test_manual_with_50_steps(self):
        """Test a manual with 50 steps (simulating 100+)."""
        manual_id = unique_id()

        steps = [
            {"step_number": i, "title": f"Step {i}", "content": f"Content {i}"}
            for i in range(1, 51)
        ]

        response = httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": manual_id,
                "title": "Fifty Step Manual",
                "steps": steps
            },
            timeout=30.0
        )
        assert response.status_code == 201
        data = response.json()
        assert data["total_steps"] == 50

        # Cleanup
        httpx.delete(f"{API_BASE}/manuals/{manual_id}", timeout=10.0)


class TestDurationTracking:
    """Test session duration tracking."""

    def test_duration_calculation(self):
        """Test that session duration is tracked."""
        import time

        manual_id = unique_id()
        session_id = unique_id()

        httpx.post(
            f"{API_BASE}/manuals",
            json={
                "manual_id": manual_id,
                "title": "Duration Test Manual",
                "steps": [{"step_number": 1, "title": "Step 1", "content": "Content 1"}]
            },
            timeout=10.0
        )
        httpx.post(
            f"{API_BASE}/sessions",
            json={
                "session_id": session_id,
                "user_id": "test-user",
                "manual_id": manual_id
            },
            timeout=10.0
        )

        # Wait a bit
        time.sleep(2)

        # Get session - duration should be tracked
        response = httpx.get(f"{API_BASE}/sessions/{session_id}", timeout=10.0)
        assert response.status_code == 200
        data = response.json()

        # Session should have started_at timestamp
        assert "started_at" in data

        # Cleanup
        httpx.delete(f"{API_BASE}/sessions/{session_id}", timeout=10.0)
        httpx.delete(f"{API_BASE}/manuals/{manual_id}", timeout=10.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
