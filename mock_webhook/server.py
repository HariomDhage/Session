"""
Mock Webhook Server - External Instruction Delivery Service Simulator

This server simulates an external instruction delivery service that receives
webhook notifications from the Session Service when progress updates occur.

It logs all received payloads for debugging and testing purposes.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mock Instruction Delivery Service",
    description="Simulates an external service that receives progress updates",
    version="1.0.0"
)

# In-memory storage for received webhooks (for demo purposes)
received_webhooks: List[Dict[str, Any]] = []


@app.post("/webhook")
async def receive_webhook(request: Request):
    """
    Receive webhook notifications from the Session Service.

    This endpoint simulates an external instruction delivery service
    that processes progress updates and session events.
    """
    try:
        payload = await request.json()

        # Add timestamp
        payload["received_at"] = datetime.utcnow().isoformat()

        # Store the webhook
        received_webhooks.append(payload)

        # Keep only last 100 webhooks in memory
        if len(received_webhooks) > 100:
            received_webhooks.pop(0)

        # Log the received webhook
        event_type = payload.get("event_type", "unknown")
        session_id = payload.get("session_id", "unknown")

        logger.info(
            f"Received {event_type} webhook for session {session_id}"
        )
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        # Simulate processing based on event type
        if event_type == "progress_update":
            current_step = payload.get("current_step", 0)
            total_steps = payload.get("total_steps", 0)
            step_status = payload.get("step_status", "")

            # Simulate determining next instruction
            next_instruction = None
            if current_step <= total_steps:
                next_instruction = {
                    "action": "deliver_instruction",
                    "step": current_step,
                    "message": f"Please proceed with step {current_step}"
                }
            else:
                next_instruction = {
                    "action": "complete",
                    "message": "All steps completed! Great job!"
                }

            return JSONResponse(
                status_code=200,
                content={
                    "status": "received",
                    "message": "Progress update processed",
                    "session_id": session_id,
                    "next_instruction": next_instruction
                }
            )

        elif event_type == "session_created":
            return JSONResponse(
                status_code=200,
                content={
                    "status": "received",
                    "message": "Session creation acknowledged",
                    "session_id": session_id,
                    "instruction": {
                        "action": "start",
                        "message": "Welcome! Let's begin with step 1."
                    }
                }
            )

        elif event_type == "session_ended":
            duration = payload.get("duration_seconds", 0)
            final_step = payload.get("final_step", 0)

            return JSONResponse(
                status_code=200,
                content={
                    "status": "received",
                    "message": "Session completion recorded",
                    "session_id": session_id,
                    "summary": {
                        "final_step": final_step,
                        "duration_seconds": duration,
                        "feedback": "Session data recorded for analytics"
                    }
                }
            )

        # Default response for unknown event types
        return JSONResponse(
            status_code=200,
            content={
                "status": "received",
                "message": f"Event '{event_type}' acknowledged"
            }
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/webhooks")
async def list_webhooks(limit: int = 20):
    """
    List recently received webhooks.

    This endpoint is useful for debugging and verifying that
    webhooks are being received correctly.
    """
    return {
        "total": len(received_webhooks),
        "showing": min(limit, len(received_webhooks)),
        "webhooks": received_webhooks[-limit:][::-1]  # Most recent first
    }


@app.delete("/webhooks")
async def clear_webhooks():
    """Clear all stored webhooks."""
    received_webhooks.clear()
    return {"message": "All webhooks cleared"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Mock Instruction Delivery Service",
        "webhooks_received": len(received_webhooks)
    }


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Mock Instruction Delivery Service",
        "description": "Simulates an external service receiving Session Service webhooks",
        "endpoints": {
            "POST /webhook": "Receive webhook notifications",
            "GET /webhooks": "List received webhooks",
            "DELETE /webhooks": "Clear stored webhooks",
            "GET /health": "Health check"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
