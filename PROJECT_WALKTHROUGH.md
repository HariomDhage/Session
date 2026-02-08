# Session Service - Complete Project Walkthrough

> A backend service for tracking user sessions with an AI agent. This document walks through every technical decision, architecture choice, and implementation detail so you can follow the full thought process behind the code.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Tech Stack & Why I Chose Each Tool](#3-tech-stack--why-i-chose-each-tool)
4. [Project Structure Explained](#4-project-structure-explained)
5. [Database Schema - Deep Dive](#5-database-schema---deep-dive)
6. [API Design - Endpoint by Endpoint](#6-api-design---endpoint-by-endpoint)
7. [Input Data Handling (Type A vs Type B/C)](#7-input-data-handling-type-a-vs-type-bc)
8. [Edge Cases - How Each One Is Handled](#8-edge-cases---how-each-one-is-handled)
9. [Webhook & Feedback System](#9-webhook--feedback-system)
10. [Background Services](#10-background-services)
11. [Concurrency & Data Integrity](#11-concurrency--data-integrity)
12. [Rate Limiting](#12-rate-limiting)
13. [Testing Strategy](#13-testing-strategy)
14. [Docker & Infrastructure](#14-docker--infrastructure)
15. [Frontend Dashboard](#15-frontend-dashboard)
16. [Request Lifecycle - Full Trace](#16-request-lifecycle---full-trace)
17. [Design Trade-offs & What I'd Change in Production](#17-design-trade-offs--what-id-change-in-production)
18. [How to Run](#18-how-to-run)

---

## 1. Problem Statement

The service needs to sit between an upstream AI agent and an external instruction delivery system. Its job:

- **Track sessions**: A user starts a session tied to a manual (set of instructional steps). The manual can have anywhere from 2 to 100+ steps.
- **Store conversations**: Every chat message (user or agent) gets saved for history.
- **Track progress**: As the user completes steps, the service records where they are and whether they finished or are still working on a step.
- **Send feedback**: When progress happens, notify an external instruction delivery service via webhook so it can decide what instruction to send next.
- **Handle edge cases**: Invalid steps, duplicates, out-of-order updates, ended sessions, missing manuals, and concurrent writes.

Session durations range from 1 second to 30+ minutes.

---

## 2. High-Level Architecture

```
                     ┌──────────────────────┐
                     │   Upstream AI Agent   │
                     └──────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
         Type A Input     Type B Input      Type C Input
         (Messages)     (Step: ONGOING)    (Step: DONE)
              │                 │                 │
              ▼                 ▼                 ▼
    ┌─────────────────────────────────────────────────────┐
    │              SESSION SERVICE (FastAPI)                │
    │                                                      │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
    │  │ Sessions │ │ Messages │ │ Progress │ │Manuals │ │
    │  │  Router  │ │  Router  │ │  Router  │ │ Router │ │
    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
    │       │            │            │            │      │
    │       └────────────┴─────┬──────┴────────────┘      │
    │                          │                           │
    │               ┌──────────▼──────────┐                │
    │               │    Service Layer    │                │
    │               │  (Business Logic)   │                │
    │               └──────────┬──────────┘                │
    │                          │                           │
    │              ┌───────────┼───────────┐               │
    │              │           │           │               │
    │        ┌─────▼─────┐ ┌──▼───┐ ┌─────▼──────┐       │
    │        │ PostgreSQL │ │Retry │ │ Background │       │
    │        │  Database  │ │Queue │ │   Tasks    │       │
    │        └───────────┘ └──┬───┘ └────────────┘       │
    │                         │                           │
    └─────────────────────────┼───────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────┐
                │ External Instruction    │
                │ Delivery Service        │
                │ (Mock Webhook Server)   │
                └─────────────────────────┘
```

The architecture is layered:

1. **Router Layer** - HTTP request handling, input validation (Pydantic), response formatting
2. **Service Layer** - All business logic, edge case checks, orchestration
3. **Model Layer** - SQLAlchemy ORM models, database constraints
4. **Infrastructure** - Database, webhook delivery, background workers

Each layer only talks to the one below it. Routers never touch the database directly. Services never format HTTP responses.

---

## 3. Tech Stack & Why I Chose Each Tool

| Technology | Role | Why This Over Alternatives |
|---|---|---|
| **FastAPI** | Web framework | Built-in async support, auto-generated Swagger docs, Pydantic validation out of the box. Django was too heavy for a microservice. Flask doesn't have native async. |
| **PostgreSQL** | Database | ACID compliance matters here because we're tracking step progress and need data consistency. SQLite can't handle concurrent writes. MongoDB doesn't give us foreign key constraints. |
| **SQLAlchemy (async)** | ORM | Mature, supports async with `asyncpg`, handles relationships and eager loading well. Raw SQL would work but becomes harder to maintain. |
| **asyncpg** | DB driver | Fastest async PostgreSQL driver for Python. Required for SQLAlchemy's async mode. |
| **Pydantic v2** | Validation | Validates all incoming data with type safety. Integrated with FastAPI. Catches bad data before it reaches the service layer. |
| **httpx** | HTTP client | Async HTTP client for webhook calls. `requests` library is synchronous and would block the event loop. |
| **Alembic** | Migrations | Standard migration tool for SQLAlchemy. Keeps schema changes versioned and reproducible. |
| **Docker Compose** | Infrastructure | 4 services (frontend, backend, db, mock webhook) running with one command. No need to install PostgreSQL locally. |
| **React + Vite** | Frontend | Fast dev server, TypeScript support. The dashboard is a bonus to visualize sessions and manuals during demo. |

---

## 4. Project Structure Explained

```
session-service/
├── app/                          # Backend application
│   ├── main.py                   # FastAPI app, lifespan events, middleware setup
│   ├── config.py                 # Environment variable loading (pydantic-settings)
│   ├── database.py               # SQLAlchemy engine, session factory, init/close
│   │
│   ├── models/                   # Database models (SQLAlchemy ORM)
│   │   ├── manual.py             # Manual + ManualStep models
│   │   ├── session.py            # Session model with version column
│   │   ├── message.py            # ConversationMessage + ProgressEvent models
│   │   └── webhook_queue.py      # WebhookQueueItem model for retry queue
│   │
│   ├── schemas/                  # Request/Response schemas (Pydantic)
│   │   ├── session.py            # SessionCreate, SessionUpdate, SessionResponse
│   │   ├── message.py            # MessageCreate, MessageResponse
│   │   ├── manual.py             # ManualCreate, ManualResponse
│   │   └── progress.py           # ProgressUpdate, ProgressResponse, StepStatus enum
│   │
│   ├── api/
│   │   ├── deps.py               # Dependency injection (database session)
│   │   └── routes/
│   │       ├── sessions.py       # CRUD endpoints for sessions
│   │       ├── messages.py       # POST/GET messages for a session
│   │       ├── progress.py       # Progress updates + next-step endpoint
│   │       ├── manuals.py        # CRUD endpoints for manuals
│   │       └── analytics.py      # Dashboard statistics endpoints
│   │
│   ├── services/                 # Business logic (all the real work happens here)
│   │   ├── session_service.py    # Session CRUD, validation, locking
│   │   ├── message_service.py    # Message storage and retrieval
│   │   ├── progress_service.py   # Step tracking, edge case handling, webhook trigger
│   │   ├── manual_service.py     # Manual CRUD and step lookup
│   │   ├── feedback_service.py   # Webhook delivery with retry fallback
│   │   ├── webhook_retry_service.py  # Background retry queue with exponential backoff
│   │   ├── analytics_service.py  # Aggregated stats and metrics
│   │   └── background_tasks.py   # Stale session cleanup, retry worker management
│   │
│   ├── middleware/
│   │   └── rate_limiter.py       # Sliding window rate limiter (per-IP)
│   │
│   └── utils/
│       └── exceptions.py         # Custom exception hierarchy with error codes
│
├── tests/                        # Test suite
│   ├── conftest.py               # Fixtures: test DB, client, sample data
│   ├── test_sessions.py          # Session CRUD tests
│   ├── test_messages.py          # Message storage tests
│   ├── test_progress.py          # Progress tracking tests
│   ├── test_edge_cases.py        # All 6 edge case scenarios
│   └── test_integration.py       # End-to-end flow tests
│
├── alembic/                      # Database migrations
│   └── versions/
│       ├── 001_initial_migration.py   # Create all tables, indexes, constraints
│       └── 002_add_webhook_queue.py   # Add webhook retry queue table
│
├── mock_webhook/                 # Simulated external service
│   └── server.py                 # FastAPI app that receives and logs webhooks
│
├── frontend/                     # React dashboard
│   └── src/
│       ├── pages/                # Dashboard, Sessions, Manuals, etc.
│       ├── services/api.ts       # Axios client for backend API
│       └── components/           # Reusable UI components
│
├── docker-compose.yml            # 4-service orchestration
├── Dockerfile                    # Backend container
├── requirements.txt              # Python dependencies
└── postman_collection.json       # Ready-to-import API collection
```

---

## 5. Database Schema - Deep Dive

### Why 5 Tables

The problem has distinct entities that map naturally to tables:

```
manuals ──1:N──► manual_steps     (a manual has many steps)
manuals ──1:N──► sessions          (a manual is used by many sessions)
sessions ──1:N──► conversation_messages  (a session has many messages)
sessions ──1:N──► progress_events        (a session has many progress events)
```

Plus `webhook_queue` for retry infrastructure.

### Table: `manuals`

```sql
CREATE TABLE manuals (
    id          UUID PRIMARY KEY,
    manual_id   VARCHAR(100) UNIQUE NOT NULL,  -- external ID from upstream
    title       VARCHAR(255) NOT NULL,
    total_steps INTEGER NOT NULL,
    created_at  VARCHAR(50) NOT NULL,
    updated_at  VARCHAR(50) NOT NULL
);
```

**Why `manual_id` and `id`?** The `id` is our internal UUID primary key. The `manual_id` is the external identifier that upstream systems use. This separation means upstream doesn't need to know about our internal IDs.

### Table: `manual_steps`

```sql
CREATE TABLE manual_steps (
    id          UUID PRIMARY KEY,
    manual_uuid UUID REFERENCES manuals(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    title       VARCHAR(255) NOT NULL,
    content     TEXT NOT NULL,
    created_at  VARCHAR(50) NOT NULL,
    UNIQUE(manual_uuid, step_number)  -- no duplicate step numbers per manual
);
```

**Why a separate table for steps?** The assignment says manuals can have 2 to 100+ steps. Storing steps as a JSON array in the manual row would make it hard to query individual steps and impossible to index them. A separate table lets us:
- Query a single step without loading the entire manual
- Add indexes on `(manual_uuid, step_number)` for fast lookups
- Enforce uniqueness: no two steps with the same number in one manual

### Table: `sessions`

```sql
CREATE TABLE sessions (
    id              UUID PRIMARY KEY,
    session_id      VARCHAR(100) UNIQUE NOT NULL,
    user_id         VARCHAR(100) NOT NULL,
    manual_uuid     UUID REFERENCES manuals(id),
    current_step    INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    started_at      VARCHAR(50) NOT NULL,
    ended_at        VARCHAR(50),
    last_activity_at VARCHAR(50) NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,     -- optimistic locking
    created_at      VARCHAR(50) NOT NULL,
    updated_at      VARCHAR(50) NOT NULL,
    CHECK (current_step >= 0),
    CHECK (status IN ('active', 'completed', 'abandoned'))
);
```

Key columns:
- **`version`** - Incremented on every update. Used for optimistic locking to detect concurrent writes. More on this in the [Concurrency section](#11-concurrency--data-integrity).
- **`last_activity_at`** - Tracks when the user last interacted. Background job uses this to auto-abandon stale sessions after 30 minutes.
- **`current_step`** - Denormalized counter. Could be derived from progress_events, but computing it on every request would be slow. This is a deliberate trade-off: slight data duplication for much faster reads.

### Table: `conversation_messages`

```sql
CREATE TABLE conversation_messages (
    id           UUID PRIMARY KEY,
    session_uuid UUID REFERENCES sessions(id) ON DELETE CASCADE,
    message_text TEXT NOT NULL,
    sender       VARCHAR(20) NOT NULL,  -- 'user', 'agent', 'system'
    step_at_time INTEGER,               -- which step the user was on
    created_at   VARCHAR(50) NOT NULL,
    CHECK (sender IN ('user', 'agent', 'system'))
);
```

**Why `step_at_time`?** It records which step the user was on when they sent the message. This lets you correlate messages with steps later for analytics ("what did users ask about during step 3?").

### Table: `progress_events`

```sql
CREATE TABLE progress_events (
    id              UUID PRIMARY KEY,
    session_uuid    UUID REFERENCES sessions(id) ON DELETE CASCADE,
    step_number     INTEGER NOT NULL,
    step_status     VARCHAR(20) NOT NULL,  -- 'DONE' or 'ONGOING'
    previous_step   INTEGER,
    processed       BOOLEAN NOT NULL DEFAULT FALSE,
    idempotency_key VARCHAR(100),
    created_at      VARCHAR(50) NOT NULL,
    UNIQUE(session_uuid, idempotency_key),
    CHECK (step_status IN ('DONE', 'ONGOING'))
);
```

This table serves two purposes:
1. **Audit trail** - Every progress event is logged, even out-of-order ones that didn't advance the session
2. **Idempotency** - The `UNIQUE(session_uuid, idempotency_key)` constraint prevents the same update from being processed twice at the database level

### Indexes

```sql
-- Session lookups (most common query)
CREATE INDEX idx_sessions_session_id ON sessions(session_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);

-- Message retrieval (always by session, ordered by time)
CREATE INDEX idx_messages_session_id ON conversation_messages(session_uuid);
CREATE INDEX idx_messages_created_at ON conversation_messages(session_uuid, created_at);

-- Step lookups (by manual + step number)
CREATE INDEX idx_manual_steps_step_number ON manual_steps(manual_uuid, step_number);

-- Idempotency checks
CREATE INDEX idx_progress_events_idempotency ON progress_events(idempotency_key);

-- Webhook retry queue
CREATE INDEX idx_webhook_queue_status ON webhook_queue(status);
CREATE INDEX idx_webhook_queue_next_retry ON webhook_queue(status, next_retry_at);
```

I indexed the columns that appear in `WHERE` clauses of the most frequent queries. The composite index on `(manual_uuid, step_number)` is especially important because every progress update needs to look up the current step content.

---

## 6. API Design - Endpoint by Endpoint

### Sessions

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `POST` | `/api/v1/sessions` | Create a new session tied to a manual |
| `GET` | `/api/v1/sessions` | List sessions with filters (user_id, status) + pagination |
| `GET` | `/api/v1/sessions/{id}` | Get single session with duration calculation |
| `PATCH` | `/api/v1/sessions/{id}` | Update session status (complete/abandon) |
| `DELETE` | `/api/v1/sessions/{id}` | Delete session and all associated data |

### Progress (nested under sessions)

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `POST` | `/api/v1/sessions/{id}/progress` | Submit a progress update (the core endpoint) |
| `GET` | `/api/v1/sessions/{id}/next-step` | Get next recommended step content |

### Messages (nested under sessions)

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `POST` | `/api/v1/sessions/{id}/messages` | Add a chat message to session history |
| `GET` | `/api/v1/sessions/{id}/messages` | Get conversation history with pagination |

### Manuals

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `POST` | `/api/v1/manuals` | Create a manual with steps |
| `GET` | `/api/v1/manuals` | List all manuals |
| `GET` | `/api/v1/manuals/{id}` | Get manual with all steps |
| `DELETE` | `/api/v1/manuals/{id}` | Delete manual |

### Analytics

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics/overview` | System-wide stats (session counts, completion rate) |
| `GET` | `/api/v1/analytics/popular-manuals` | Most used manuals with completion rates |
| `GET` | `/api/v1/analytics/recent-activity` | Activity in last N hours |
| `GET` | `/api/v1/analytics/users/{id}` | Per-user statistics |
| `GET` | `/api/v1/analytics/manuals/{id}/steps` | Step-by-step drop-off analytics |

### Why Nested Routes

Progress and messages are nested under `/sessions/{id}/...` because they belong to a session. This makes the URL hierarchy intuitive:

```
/sessions/session-456                    → the session itself
/sessions/session-456/progress           → progress updates for that session
/sessions/session-456/messages           → messages in that session
/sessions/session-456/next-step          → what step to do next
```

---

## 7. Input Data Handling (Type A vs Type B/C)

The upstream AI agent sends two different types of data:

### Type A: Chat Messages

```json
POST /api/v1/sessions/session-456/messages
{
    "user_id": "user-123",
    "message": "I finished the hello world program!",
    "sender": "user"
}
```

**Processing flow:**
```
Request → Validate schema (Pydantic) → Check session exists → Check session is active
→ Store message in conversation_messages → Update session last_activity_at → Return
```

Messages are simple: validate, store, done. No side effects, no webhook.

### Type B/C: Progress Updates

```json
POST /api/v1/sessions/session-456/progress
{
    "user_id": "user-123",
    "current_step": 2,
    "step_status": "DONE",
    "idempotency_key": "progress-uuid-123"
}
```

**Processing flow:**
```
Request → Validate schema → Get session with row lock → Check session active
→ Validate step bounds → Check idempotency key → Handle out-of-order
→ Record progress event → If DONE: increment current_step
→ If final step: mark session completed → Send webhook → Return next step info
```

This is the most complex endpoint. It touches 6 different edge cases and triggers an external webhook.

### Why Separate Endpoints

I split messages and progress into separate endpoints because:

1. **Different data shapes** - Messages have `message` + `sender`. Progress has `current_step` + `step_status`. A combined endpoint would need conditional logic.
2. **Different processing complexity** - Messages are insert-only. Progress needs locking, validation, webhooks.
3. **Different validation rules** - Progress needs step bounds checking and idempotency. Messages don't.
4. **Independent scaling** - In production, you could put message storage on a faster queue while progress goes through the full validation pipeline.

---

## 8. Edge Cases - How Each One Is Handled

### Edge Case 1: Invalid Step Numbers

**Scenario:** Upstream sends step 10, but the manual only has 5 steps.

**Where it's handled:** `progress_service.py:63-67`

```python
if progress_data.current_step < 1:
    raise InvalidStepError("Step number must be >= 1")
if progress_data.current_step > manual.total_steps:
    raise InvalidStepError(
        f"Step {progress_data.current_step} exceeds manual's total steps ({manual.total_steps})"
    )
```

Plus Pydantic catches zero and negative values at the schema level:

```python
current_step: int = Field(..., ge=1)  # ge=1 means >= 1
```

**Response:** `400 Bad Request` with error code `INVALID_STEP_NUMBER`

---

### Edge Case 2: Duplicate Updates

**Scenario:** Network retry sends the same progress update twice.

**Where it's handled:** `progress_service.py:71-79`

```python
if progress_data.idempotency_key:
    existing = await self.db.execute(
        select(ProgressEvent).where(
            ProgressEvent.session_uuid == session.id,
            ProgressEvent.idempotency_key == progress_data.idempotency_key
        )
    )
    if existing.scalar_one_or_none():
        raise DuplicateProgressUpdateError(progress_data.idempotency_key)
```

**How it works:**
- Client sends an optional `idempotency_key` with each request
- First request: key doesn't exist → process normally, store the key in `progress_events`
- Second request with same key: key exists → reject with `409 Conflict`
- Database has a `UNIQUE(session_uuid, idempotency_key)` constraint as a safety net

**Response:** `409 Conflict` with `status: "already_processed"`

---

### Edge Case 3: Out-of-Order Updates

**Scenario:** Step 3 arrives before step 2 (network delay, async processing).

**Where it's handled:** `progress_service.py:82-88`

```python
if progress_data.current_step < session.current_step:
    logger.warning(
        f"Received update for step {progress_data.current_step} but session "
        f"is already on step {session.current_step}"
    )
    # Accept but don't regress
```

**Strategy:**
- The update is always **accepted** and logged in `progress_events` for the audit trail
- But the session's `current_step` only moves **forward**, never backward
- The `should_increment` flag (line 97-98) only becomes True if the step >= current step AND status is DONE

**Response:** `200 OK` but `current_step` stays where it was

---

### Edge Case 4: Session Already Ended

**Scenario:** Progress update arrives after session is completed or abandoned.

**Where it's handled:** `session_service.py:176-179`

```python
def validate_session_active(self, session: Session) -> None:
    if session.status != "active":
        raise SessionEndedError(session.session_id, session.status)
```

Called at the very beginning of progress processing (line 57 in progress_service.py), before any other validation.

**Response:** `400 Bad Request` with `error_code: "SESSION_ENDED"` and `current_status` in details

---

### Edge Case 5: Missing Manual

**Scenario:** Creating a session that references a manual_id that doesn't exist.

**Where it's handled:** `session_service.py:40`

```python
manual = await self.manual_service.get_manual_by_id(session_data.manual_id)
# get_manual_by_id raises ManualNotFoundError if not found
```

**Response:** `404 Not Found` with `error_code: "MANUAL_NOT_FOUND"`

---

### Edge Case 6: Concurrent Updates

**Scenario:** Two progress updates hit simultaneously for the same session.

**Where it's handled:** `session_service.py:82-95`

```python
async def get_session_with_lock(self, session_id: str) -> Session:
    result = await self.db.execute(
        select(Session)
        .where(Session.session_id == session_id)
        .with_for_update()  # PostgreSQL row-level lock
    )
```

**Two-layer protection:**
1. **Row-level lock (`SELECT ... FOR UPDATE`)** - When a progress update starts, it locks the session row. Any other concurrent request for the same session will block until the first one commits.
2. **Version column** - The `version` field is incremented on every update. If somehow two writes slip through, the version mismatch would be caught.

**Response:** `409 Conflict` with `retry: true` in details

---

### Edge Case Decision Flow

```
Progress Update Arrives
        │
        ▼
   Session exists? ──No──► 404 Not Found
        │ Yes
        ▼
   Session active? ──No──► 400 Session Ended
        │ Yes
        ▼
   Step in bounds? ──No──► 400 Invalid Step
   (1 ≤ step ≤ total)
        │ Yes
        ▼
   Duplicate key? ──Yes──► 409 Already Processed
        │ No
        ▼
   Out of order? ──Yes──► 200 OK (accept, don't regress)
   (step < current)
        │ No
        ▼
   Process normally
   ├── Record in progress_events
   ├── If DONE → increment current_step
   ├── If final step → mark completed
   ├── Send webhook
   └── Return next step info
```

---

## 9. Webhook & Feedback System

### How It Works

When a progress update with `step_status: "DONE"` is processed, the service sends a webhook to the external instruction delivery service.

**File:** `feedback_service.py`

```python
payload = {
    "event_type": "progress_update",
    "session_id": session.session_id,
    "user_id": session.user_id,
    "manual_id": manual.manual_id,
    "previous_step": previous_step,
    "current_step": session.current_step,
    "total_steps": manual.total_steps,
    "step_status": step_status,
    "session_status": session.status,
    "session_duration_seconds": session.duration_seconds,
    "is_completed": session.current_step > manual.total_steps
}
```

### Three Event Types

| Event | When | Payload Includes |
|-------|------|-----------------|
| `session_created` | New session starts | session_id, manual_id, total_steps |
| `progress_update` | Step completed/ongoing | previous_step, current_step, duration |
| `session_ended` | Session completes or is abandoned | final_step, duration, status |

### Retry Mechanism

If the webhook fails (timeout, 5xx, network error), it doesn't just fail silently:

**File:** `webhook_retry_service.py`

1. **Immediate attempt** - Try to send the webhook right away
2. **If that fails** - Queue it in the `webhook_queue` database table
3. **Background worker** - Runs every 5 seconds, picks up pending items
4. **Exponential backoff** - Retries at 4s, 16s, 64s intervals
5. **Max 3 attempts** - After 3 failures, marked as permanently failed

```python
def _calculate_next_retry(self, attempt: int) -> str:
    delay_seconds = self.BASE_DELAY_SECONDS * (4 ** (attempt - 1))
    # Attempt 1: 4 seconds
    # Attempt 2: 16 seconds
    # Attempt 3: 64 seconds
```

The queue is stored in the database (not in-memory) so pending webhooks survive server restarts.

### Mock Webhook Server

The `mock_webhook/server.py` simulates the external service. It:
- Receives webhooks and logs them
- Stores last 100 webhooks in memory
- Has a `GET /webhooks` endpoint to inspect received payloads
- Has a `DELETE /webhooks` endpoint to clear them

This makes it easy to verify webhooks are working during development and demos.

---

## 10. Background Services

**File:** `background_tasks.py`

Two background tasks run alongside the API server:

### 1. Stale Session Cleanup (every 5 minutes)

```python
async def cleanup_stale_sessions(self):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    result = await db.execute(
        update(Session)
        .where(Session.status == "active", Session.last_activity_at < cutoff_str)
        .values(status="abandoned", ended_at=now)
    )
```

If a session hasn't had any activity for 30 minutes, it's automatically marked as `abandoned`. This handles the case where users close their browser without explicitly ending the session.

### 2. Webhook Retry Worker (every 5 seconds)

Picks up failed webhooks from the `webhook_queue` table and retries them with exponential backoff. Described in detail in the webhook section above.

Both tasks are managed via FastAPI's `lifespan` context manager, which means they start when the server starts and gracefully shut down when the server stops.

---

## 11. Concurrency & Data Integrity

### The Problem

If two progress updates arrive at the exact same time for the same session, both could read `current_step = 1`, both increment to 2, and we'd lose one step advancement.

### The Solution: Two Layers

**Layer 1 - Row-level lock (`SELECT ... FOR UPDATE`)**

```python
# session_service.py:84
select(Session).where(...).with_for_update()
```

This tells PostgreSQL to lock the row when we read it. Any other transaction trying to read the same row with `FOR UPDATE` will wait. This is the primary protection.

**Layer 2 - Optimistic locking (version column)**

```python
# session.py:36
version = Column(Integer, nullable=False, default=1)

# progress_service.py:114
session.version += 1
```

Every update bumps the version. If somehow two writes occurred concurrently (theoretically prevented by layer 1, but defense in depth), the version would catch it.

### Database-Level Constraints

```sql
CHECK (current_step >= 0)
CHECK (status IN ('active', 'completed', 'abandoned'))
CHECK (sender IN ('user', 'agent', 'system'))
CHECK (step_status IN ('DONE', 'ONGOING'))
UNIQUE(manual_uuid, step_number)
UNIQUE(session_uuid, idempotency_key)
```

Even if the application logic has a bug, these database constraints prevent invalid data from being persisted.

---

## 12. Rate Limiting

**File:** `middleware/rate_limiter.py`

A sliding window rate limiter that tracks requests per client IP:

- **100 requests per minute** per IP
- **2000 requests per hour** per IP
- Returns `429 Too Many Requests` with `Retry-After` header
- Adds `X-RateLimit-Remaining-Minute` and `X-RateLimit-Remaining-Hour` headers to every response
- Excluded paths: `/`, `/health`, `/docs`, `/redoc`
- Can be disabled via `DISABLE_RATE_LIMIT=true` environment variable (for development)

In production, I'd replace this with a Redis-based implementation for distributed rate limiting across multiple server instances.

---

## 13. Testing Strategy

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── test_sessions.py      # Session CRUD
├── test_messages.py      # Message operations
├── test_progress.py      # Progress tracking
├── test_edge_cases.py    # All 6 edge cases
└── test_integration.py   # Full flow tests
```

### How Tests Work

Tests use the real PostgreSQL database (not SQLite or mocks) via the running Docker container:

```python
# conftest.py
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/sessions"
```

Each test function gets:
1. A fresh database session
2. All tables created
3. After the test: all data is deleted (but tables remain)

This approach tests the actual SQL constraints, indexes, and PostgreSQL-specific features.

### Edge Case Tests (test_edge_cases.py)

| Test Class | What It Tests |
|---|---|
| `TestInvalidStepNumbers` | Step > total, step = 0, step < 0 |
| `TestDuplicateUpdates` | Same idempotency key, different keys |
| `TestOutOfOrderUpdates` | Step update for already-passed step |
| `TestSessionAlreadyEnded` | Progress on completed session, abandoned session |
| `TestMissingManual` | Session with non-existent manual, GET non-existent manual |
| `TestVariableManualSteps` | 2-step manual, 50-step manual |
| `TestSessionDuration` | Duration calculation on active sessions |

### Running Tests

```bash
# Inside Docker
docker compose exec app pytest -v

# Locally (with database running)
pytest -v

# With coverage report
pytest --cov=app --cov-report=html
```

---

## 14. Docker & Infrastructure

### docker-compose.yml - 4 Services

```yaml
services:
  frontend:     # React dashboard (port 3000)
  app:          # FastAPI backend (port 8000)
  db:           # PostgreSQL 15 (port 5432)
  mock_webhook: # Webhook receiver (port 8001)
```

### Service Dependencies

```
db (healthcheck: pg_isready) ──► app ──► frontend
mock_webhook ──► app
```

- The backend (`app`) waits for the database to be healthy before starting
- The frontend waits for the backend
- PostgreSQL uses a health check (`pg_isready`) so Docker knows when it's actually ready to accept connections

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Key decisions:
- `python:3.11-slim` instead of full image (smaller, faster builds)
- Requirements copied first (Docker layer caching: dependencies are rebuilt only if requirements.txt changes)
- `PYTHONDONTWRITEBYTECODE=1` prevents `.pyc` file creation in the container

### Networking

All services share a Docker bridge network (`session-network`), so they can reach each other by container name:
- Backend calls database at `db:5432`
- Backend calls webhook at `mock_webhook:8001`
- Frontend calls backend at `localhost:8000` (from browser)

---

## 15. Frontend Dashboard

The React frontend provides a visual interface for managing and monitoring sessions. Built with:

- **React 18** + TypeScript
- **Vite** for fast HMR (hot module replacement)
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Axios** for API calls

### Pages

| Page | Route | What It Shows |
|------|-------|--------------|
| Dashboard | `/` | Overview stats, recent activity, quick links |
| Manuals | `/manuals` | Grid of all manuals with step counts |
| Manual Detail | `/manuals/:id` | All steps in a manual |
| Create Manual | `/manuals/create` | Form to create a new manual with steps |
| Sessions | `/sessions` | Table of all sessions with status filters |
| Session Detail | `/sessions/:id` | Progress bar, messages, step completion |
| Create Session | `/sessions/create` | Form to start a new session |

The Session Detail page is the most interactive - it shows a live progress bar, lets you mark steps as complete, send messages, and end the session.

---

## 16. Request Lifecycle - Full Trace

Let's trace what happens when a `POST /api/v1/sessions/session-456/progress` request arrives with `step_status: "DONE"`:

```
1. Request arrives at uvicorn
2. CORS middleware adds headers
3. RequestIDMiddleware adds X-Request-ID
4. RateLimitMiddleware checks IP against sliding window
5. FastAPI routes to progress.py:update_progress()
6. Pydantic validates the request body (ProgressUpdate schema)
7. Dependency injection provides database session
8. ProgressService.update_progress() is called
   a. SessionService.get_session_with_lock() → SELECT ... FOR UPDATE
   b. validate_session_active() → is status == 'active'?
   c. ManualService.get_manual_by_uuid() → load the manual
   d. Check step bounds (1 ≤ step ≤ total_steps)
   e. Check idempotency key (SELECT from progress_events)
   f. Check out-of-order (step < current_step?)
   g. Create ProgressEvent record
   h. If DONE: increment session.current_step, bump version
   i. If final step: set status = 'completed', set ended_at
   j. Update last_activity_at
   k. COMMIT transaction (releases row lock)
9. FeedbackService.send_progress_update() fires webhook
   a. Build payload with session + manual data
   b. httpx.AsyncClient.post() to WEBHOOK_URL
   c. If fails: queue in webhook_queue for background retry
10. Build ProgressResponse with next_step info
11. Return JSON response with 200 OK
12. Rate limit headers added to response
```

---

## 17. Design Trade-offs & What I'd Change in Production

### Current Trade-offs

| Decision | Trade-off | Why It's Acceptable |
|----------|-----------|-------------------|
| **In-memory rate limiter** | Doesn't work across multiple server instances | Single instance is fine for this scale. Redis would fix it for multi-instance. |
| **Timestamps as strings** | Slightly harder to query by date range | Avoids timezone handling complexity with PostgreSQL timestamp types. Works fine for current query patterns. |
| **Denormalized `total_steps` in session** | Data could get out of sync if manual is edited | Manuals are reference data that shouldn't change after sessions use them. |
| **Webhook retry in same process** | Webhook failures could slow down the event loop | For current scale, async tasks handle it. A dedicated worker (Celery) would be better at scale. |
| **Mock webhook in Docker Compose** | Not a real external service | Demonstrates the integration pattern. Replace URL in config for production. |

### What I'd Add for Production

1. **Redis** - For rate limiting, session caching, and webhook pub/sub
2. **Celery** - Dedicated task queue for webhooks instead of in-process background tasks
3. **Authentication middleware** - JWT validation or API key checking
4. **Request logging** - Structured logging with correlation IDs (the X-Request-ID header is already there)
5. **Monitoring** - Prometheus metrics, health check dashboard
6. **Connection pooling** - PgBouncer between the app and PostgreSQL
7. **CI/CD** - The `.github/workflows/ci.yml` is there, just needs environment configuration

---

## 18. How to Run

### Docker (recommended)

```bash
cd session-service

# Start everything
docker compose up -d

# Check logs
docker compose logs -f

# Stop
docker compose down

# Stop + wipe database
docker compose down -v
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000/api/v1 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |
| Mock Webhook | http://localhost:8001 |
| Received Webhooks | http://localhost:8001/webhooks |

### Quick Demo Flow

```bash
# 1. Create a manual
curl -X POST http://localhost:8000/api/v1/manuals \
  -H "Content-Type: application/json" \
  -d '{
    "manual_id": "python-101",
    "title": "Introduction to Python",
    "steps": [
      {"step_number": 1, "title": "Hello World", "content": "Write print(\"Hello World\")"},
      {"step_number": 2, "title": "Variables", "content": "Create a variable x = 5"},
      {"step_number": 3, "title": "Functions", "content": "Define a function with def"}
    ]
  }'

# 2. Start a session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session-1",
    "user_id": "hariom",
    "manual_id": "python-101"
  }'

# 3. Send a message
curl -X POST http://localhost:8000/api/v1/sessions/demo-session-1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "hariom",
    "message": "I wrote the hello world program!",
    "sender": "user"
  }'

# 4. Complete step 1
curl -X POST http://localhost:8000/api/v1/sessions/demo-session-1/progress \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "hariom",
    "current_step": 1,
    "step_status": "DONE",
    "idempotency_key": "step-1-done"
  }'

# 5. Check what webhook received
curl http://localhost:8001/webhooks

# 6. Get next step recommendation
curl http://localhost:8000/api/v1/sessions/demo-session-1/next-step

# 7. Check dashboard stats
curl http://localhost:8000/api/v1/analytics/overview
```

---

*Built with FastAPI, PostgreSQL, React, and Docker.*
