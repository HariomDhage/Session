#!/usr/bin/env python3
"""
Demo Data Seeding Script

Creates realistic demo data for impressive presentations:
- 3 sample manuals with different step counts (5, 8, 12 steps)
- 10+ sessions in various states (active, completed, abandoned)
- Conversation history for each session
- Progress events showing user journey

Run: python scripts/seed_demo_data.py
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import httpx

API_BASE = "http://localhost:8000/api/v1"

# Sample manuals with varying complexity
SAMPLE_MANUALS = [
    {
        "manual_id": "python-basics",
        "title": "Python Programming Basics",
        "steps": [
            {"step_number": 1, "title": "Introduction to Python", "content": "Python is a versatile programming language. Let's start by understanding what Python is and why it's so popular."},
            {"step_number": 2, "title": "Setting Up Your Environment", "content": "Install Python from python.org and set up your IDE. We recommend VS Code or PyCharm."},
            {"step_number": 3, "title": "Variables and Data Types", "content": "Learn about integers, floats, strings, and booleans. Try: x = 10, name = 'Alice'"},
            {"step_number": 4, "title": "Control Flow", "content": "Master if/else statements and loops. Example: for i in range(5): print(i)"},
            {"step_number": 5, "title": "Functions", "content": "Create reusable code blocks. def greet(name): return f'Hello, {name}!'"},
        ]
    },
    {
        "manual_id": "react-fundamentals",
        "title": "React.js Fundamentals",
        "steps": [
            {"step_number": 1, "title": "What is React?", "content": "React is a JavaScript library for building user interfaces. Created by Facebook."},
            {"step_number": 2, "title": "Setting Up React", "content": "Use Create React App or Vite: npx create-react-app my-app"},
            {"step_number": 3, "title": "JSX Basics", "content": "JSX lets you write HTML-like syntax in JavaScript. Example: <h1>Hello World</h1>"},
            {"step_number": 4, "title": "Components", "content": "Build reusable UI pieces. Function components are the modern approach."},
            {"step_number": 5, "title": "Props", "content": "Pass data to components: <Greeting name='Alice' />"},
            {"step_number": 6, "title": "State with useState", "content": "Manage component state: const [count, setCount] = useState(0)"},
            {"step_number": 7, "title": "useEffect Hook", "content": "Handle side effects like API calls and subscriptions."},
            {"step_number": 8, "title": "Building Your First App", "content": "Combine everything to build a complete React application!"},
        ]
    },
    {
        "manual_id": "api-design-masterclass",
        "title": "REST API Design Masterclass",
        "steps": [
            {"step_number": 1, "title": "REST Principles", "content": "Understand RESTful architecture: resources, HTTP methods, statelessness."},
            {"step_number": 2, "title": "HTTP Methods", "content": "GET, POST, PUT, PATCH, DELETE - when to use each one."},
            {"step_number": 3, "title": "URL Design", "content": "Design clean, intuitive URLs: /users, /users/{id}, /users/{id}/posts"},
            {"step_number": 4, "title": "Request/Response Format", "content": "JSON structure, headers, content-type negotiation."},
            {"step_number": 5, "title": "Status Codes", "content": "200 OK, 201 Created, 400 Bad Request, 404 Not Found, 500 Server Error"},
            {"step_number": 6, "title": "Authentication", "content": "JWT tokens, OAuth 2.0, API keys - choose the right approach."},
            {"step_number": 7, "title": "Pagination", "content": "Handle large datasets: offset/limit, cursor-based pagination."},
            {"step_number": 8, "title": "Rate Limiting", "content": "Protect your API from abuse with rate limiting strategies."},
            {"step_number": 9, "title": "Versioning", "content": "API versioning strategies: URL path, headers, query params."},
            {"step_number": 10, "title": "Error Handling", "content": "Consistent error responses with error codes and messages."},
            {"step_number": 11, "title": "Documentation", "content": "OpenAPI/Swagger, API documentation best practices."},
            {"step_number": 12, "title": "Testing Your API", "content": "Unit tests, integration tests, Postman collections."},
        ]
    },
]

# Sample user names for realistic sessions
USERS = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "henry", "ivy", "jack"]

# Sample conversation messages
SAMPLE_MESSAGES = {
    "user": [
        "I've completed this step!",
        "This makes sense now.",
        "Can you explain more about this?",
        "Got it, moving to the next step.",
        "I understand this concept.",
        "Thanks for the clear explanation!",
        "This is helpful.",
        "I'm ready for the next step.",
    ],
    "agent": [
        "Great job! Let's move on to the next concept.",
        "Well done! You're making excellent progress.",
        "Perfect! That's exactly right.",
        "You've got it! Ready for the next challenge?",
        "Excellent understanding! Keep going.",
        "That's correct! You're doing great.",
    ],
    "system": [
        "Session started.",
        "Progress saved.",
        "Step completed successfully.",
    ]
}


async def create_manual(client: httpx.AsyncClient, manual_data: dict) -> dict | None:
    """Create a manual via API."""
    try:
        response = await client.post(f"{API_BASE}/manuals", json=manual_data)
        if response.status_code == 201:
            print(f"  ✓ Created manual: {manual_data['title']}")
            return response.json()
        elif response.status_code == 409:
            print(f"  • Manual already exists: {manual_data['title']}")
            # Fetch existing
            get_response = await client.get(f"{API_BASE}/manuals/{manual_data['manual_id']}")
            return get_response.json() if get_response.status_code == 200 else None
        else:
            print(f"  ✗ Failed to create manual: {response.text}")
            return None
    except Exception as e:
        print(f"  ✗ Error creating manual: {e}")
        return None


async def create_session(client: httpx.AsyncClient, session_data: dict) -> dict | None:
    """Create a session via API."""
    try:
        response = await client.post(f"{API_BASE}/sessions", json=session_data)
        if response.status_code == 201:
            return response.json()
        else:
            print(f"  ✗ Failed to create session: {response.text}")
            return None
    except Exception as e:
        print(f"  ✗ Error creating session: {e}")
        return None


async def add_message(client: httpx.AsyncClient, session_id: str, message_data: dict) -> bool:
    """Add a message to a session."""
    try:
        response = await client.post(f"{API_BASE}/sessions/{session_id}/messages", json=message_data)
        return response.status_code == 201
    except Exception:
        return False


async def update_progress(client: httpx.AsyncClient, session_id: str, progress_data: dict) -> dict | None:
    """Update progress for a session."""
    try:
        response = await client.post(f"{API_BASE}/sessions/{session_id}/progress", json=progress_data)
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None


async def end_session(client: httpx.AsyncClient, session_id: str, status: str) -> bool:
    """End a session with given status."""
    try:
        response = await client.patch(f"{API_BASE}/sessions/{session_id}", json={"status": status})
        return response.status_code == 200
    except Exception:
        return False


async def simulate_session(client: httpx.AsyncClient, manual: dict, user_id: str, completion_level: str):
    """
    Simulate a user session with realistic behavior.

    completion_level: 'full', 'partial', 'abandoned', 'active'
    """
    session_id = f"session-{user_id}-{manual['manual_id'][:6]}-{uuid4().hex[:6]}"

    # Create session
    session = await create_session(client, {
        "session_id": session_id,
        "user_id": user_id,
        "manual_id": manual["manual_id"],
    })

    if not session:
        return None

    total_steps = manual["total_steps"]

    # Determine how many steps to complete
    if completion_level == "full":
        steps_to_complete = total_steps
    elif completion_level == "partial":
        steps_to_complete = random.randint(2, total_steps - 1)
    elif completion_level == "abandoned":
        steps_to_complete = random.randint(1, max(2, total_steps // 3))
    else:  # active
        steps_to_complete = random.randint(1, total_steps - 1)

    # Simulate going through steps
    for step in range(1, steps_to_complete + 1):
        # Add user message
        await add_message(client, session_id, {
            "user_id": user_id,
            "message": random.choice(SAMPLE_MESSAGES["user"]),
            "sender": "user"
        })

        # Add agent response
        await add_message(client, session_id, {
            "user_id": user_id,
            "message": random.choice(SAMPLE_MESSAGES["agent"]),
            "sender": "agent"
        })

        # Update progress (mark step as done)
        await update_progress(client, session_id, {
            "user_id": user_id,
            "current_step": step,
            "step_status": "DONE",
            "idempotency_key": f"{session_id}-step-{step}"
        })

        # Small delay to make timestamps realistic
        await asyncio.sleep(0.05)

    # End session if not active
    if completion_level == "abandoned":
        await end_session(client, session_id, "abandoned")
    elif completion_level == "full":
        # Already completed through progress updates
        pass

    return session_id


async def main():
    """Main seeding function."""
    print("\n" + "=" * 60)
    print("🌱 Session Service - Demo Data Seeding")
    print("=" * 60 + "\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check API health
        try:
            health = await client.get("http://localhost:8000/health")
            if health.status_code != 200:
                print("❌ API is not healthy. Start the service first.")
                return
            print("✓ API is healthy\n")
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print("  Make sure to run: docker-compose up")
            return

        # Create manuals
        print("📚 Creating Manuals...")
        manuals = []
        for manual_data in SAMPLE_MANUALS:
            manual = await create_manual(client, manual_data)
            if manual:
                manuals.append(manual)

        print(f"\n✓ {len(manuals)} manuals ready\n")

        if not manuals:
            print("❌ No manuals created. Cannot proceed.")
            return

        # Create sessions with various states
        print("👥 Creating Demo Sessions...")
        sessions_created = 0

        for i, user in enumerate(USERS):
            # Each user gets 1-2 sessions
            num_sessions = random.randint(1, 2)

            for _ in range(num_sessions):
                manual = random.choice(manuals)

                # Distribute session states
                if i < 3:
                    completion = "full"  # First 3 users complete
                elif i < 5:
                    completion = "partial"  # Next 2 partially complete
                elif i < 7:
                    completion = "active"  # Next 2 are still active
                else:
                    completion = "abandoned"  # Rest abandoned

                session_id = await simulate_session(client, manual, user, completion)
                if session_id:
                    sessions_created += 1
                    status_emoji = {"full": "✅", "partial": "🔄", "active": "▶️", "abandoned": "⏹️"}
                    print(f"  {status_emoji[completion]} {session_id[:30]}... ({completion})")

        print(f"\n✓ {sessions_created} sessions created\n")

        # Print summary
        print("=" * 60)
        print("📊 Demo Data Summary")
        print("=" * 60)

        # Fetch stats
        try:
            overview = await client.get(f"{API_BASE}/analytics/overview")
            if overview.status_code == 200:
                stats = overview.json()
                print(f"\n  Manuals: {stats['manuals']['total']}")
                print(f"  Sessions: {stats['sessions']['total']}")
                print(f"    - Active: {stats['sessions']['active']}")
                print(f"    - Completed: {stats['sessions']['completed']}")
                print(f"    - Abandoned: {stats['sessions']['abandoned']}")
                print(f"  Messages: {stats['messages']['total']}")
                print(f"  Completion Rate: {stats['metrics']['completion_rate_percent']}%")
        except Exception:
            pass

        print("\n" + "=" * 60)
        print("🎉 Demo data ready! Visit:")
        print("   • Frontend: http://localhost:3000")
        print("   • Swagger: http://localhost:8000/docs")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
