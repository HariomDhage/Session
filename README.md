# Session Service

A backend service for tracking user sessions with an AI agent. Built with FastAPI, PostgreSQL, and React for the dashboard.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start) - How to set up and run with Docker
- [Frontend Dashboard](#frontend-dashboard)
- [Architecture](#architecture)
- [Database Schema](#database-schema) - Schema design and rationale
- [API Design](#api-design) - API structure and design decisions
- [Input Data Handling](#input-data-handling) - Type A and Type B/C inputs
- [Edge Cases](#edge-cases) - Handling all 6 edge cases
- [Feedback Mechanism](#feedback-mechanism) - Webhook integration
- [Configuration](#configuration)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [Assumptions](#assumptions)

## Features

- **Session Management**: Create, retrieve, update, and delete user sessions
- **Progress Tracking**: Track user progress through instructional steps with a flexible counter
- **Conversation Storage**: Store and retrieve full conversation transcripts
- **Session Duration**: Accurate tracking for sessions from 1 second to 30+ minutes
- **Feedback Mechanism**: Webhook integration with external instruction delivery service
- **Edge Case Handling**: Comprehensive handling of all specified edge cases
- **Frontend Dashboard**: React + Tailwind CSS dashboard for visual management

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) PostgreSQL for production deployment

### Running with Docker Compose (Recommended)

```bash
cd session-service

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down

# Stop and reset database
docker compose down -v
```

**Services will be available at:**
- Frontend Dashboard: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Mock Webhook: http://localhost:8001

### Running Manually (Without Docker)

**1. Start Database:**
```bash
docker run -d --name session-db -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=sessions \
  postgres:15-alpine
```

**2. Start Backend:**
```bash
cd session-service

# Install dependencies
pip install -r requirements.txt

# Set environment variables (Windows)
set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sessions
set WEBHOOK_URL=http://localhost:8001/webhook
set WEBHOOK_ENABLED=true
set DISABLE_RATE_LIMIT=true

# Run backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**3. Start Frontend:**
```bash
cd session-service/frontend

# Install dependencies
npm install

# Set API URL (Windows)
set VITE_API_URL=http://localhost:8000/api/v1

# Run frontend
npm run dev
```

## Frontend Dashboard

The frontend is a React application built with Vite and Tailwind CSS.

### Features

- **Dashboard**: Overview of sessions and manuals with statistics
- **Manual Management**: Create, view, and delete instruction manuals
- **Session Management**: Create sessions, track progress, and manage status
- **Interactive Session View**:
  - Real-time progress tracking with visual step indicator
  - Conversation display with message history
  - Step completion with one-click action
  - Session duration tracking

### Screenshots

The dashboard provides:

1. **Overview Dashboard** - Statistics and recent activity
2. **Manuals List** - Grid view of all instruction manuals
3. **Manual Detail** - View all steps in a manual
4. **Sessions List** - Table view with filters (active/completed/abandoned)
5. **Session Detail** - Interactive view with:
   - Current step content and instructions
   - Progress bar and step indicators
   - Real-time conversation/chat panel
   - Complete step and end session actions

### Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Axios** for API calls
- **Lucide React** for icons

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT / UPSTREAM AI                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP Requests
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SESSION SERVICE (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Sessions  │  │  Messages   │  │  Progress   │  │   Manuals   │    │
│  │   Router    │  │   Router    │  │   Router    │  │   Router    │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │                │            │
│         └────────────────┼────────────────┼────────────────┘            │
│                          ▼                ▼                             │
│               ┌─────────────────────────────────────┐                   │
│               │         SERVICE LAYER               │                   │
│               │  SessionService | ProgressService   │                   │
│               │  MessageService | FeedbackService   │                   │
│               └─────────────────┬───────────────────┘                   │
│                                 │                                        │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│   PostgreSQL     │  │   Feedback       │  │  External Instruction    │
│   Database       │  │   Webhook Call   │  │  Delivery Service        │
│                  │  │                  │  │  (Mock Server)           │
│  - manuals       │  └────────┬─────────┘  │                          │
│  - manual_steps  │           │            │  Receives:               │
│  - sessions      │           └───────────►│  - session_id            │
│  - messages      │                        │  - current_step          │
│  - progress_events                        │  - total_steps           │
└──────────────────┘                        │  - session_duration      │
                                            └──────────────────────────┘
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     Manual      │       │     Session     │       │     Message     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │───┐   │ id (PK)         │───┐   │ id (PK)         │
│ manual_id (UQ)  │   │   │ session_id (UQ) │   │   │ session_uuid    │──→ Session
│ title           │   └──→│ manual_uuid     │   │   │ sender          │
│ total_steps     │       │ user_id         │   │   │ message_text    │
│ created_at      │       │ current_step    │   │   │ created_at      │
└─────────────────┘       │ status          │   │   └─────────────────┘
         │                │ started_at      │   │
         │                │ ended_at        │   │   ┌─────────────────┐
         ▼                │ version         │   │   │  ProgressEvent  │
┌─────────────────┐       └─────────────────┘   │   ├─────────────────┤
│   ManualStep    │                             └──→│ id (PK)         │
├─────────────────┤                                 │ session_uuid    │
│ id (PK)         │                                 │ step_number     │
│ manual_uuid     │──→ Manual                       │ step_status     │
│ step_number     │                                 │ idempotency_key │
│ title           │                                 │ created_at      │
│ content         │                                 └─────────────────┘
└─────────────────┘
```

### Tables

#### 1. `manuals` - Instruction Manual Metadata

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| manual_id | VARCHAR(100) | Unique external identifier |
| title | VARCHAR(255) | Manual title |
| total_steps | INTEGER | Number of steps (2-100+) |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |

#### 2. `manual_steps` - Individual Steps (Supports 2-100+ steps)

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| manual_uuid | UUID | Foreign key to manuals |
| step_number | INTEGER | Step number (1-indexed) |
| title | VARCHAR(255) | Step title |
| content | TEXT | Step instructions |
| created_at | TIMESTAMP | Creation time |

#### 3. `sessions` - User Sessions

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| session_id | VARCHAR(100) | Unique external identifier |
| user_id | VARCHAR(100) | User identifier |
| manual_uuid | UUID | Foreign key to manuals |
| current_step | INTEGER | Current step counter |
| total_steps | INTEGER | Denormalized for quick access |
| status | VARCHAR(20) | active/completed/ended |
| started_at | TIMESTAMP | Session start time |
| ended_at | TIMESTAMP | Session end time |
| version | INTEGER | Optimistic locking version |

#### 4. `conversation_messages` - Chat History

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| session_uuid | UUID | Foreign key to sessions |
| message_text | TEXT | Message content |
| sender | VARCHAR(20) | user/agent |
| created_at | TIMESTAMP | Message time |

#### 5. `progress_events` - Audit Trail

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| session_uuid | UUID | Foreign key to sessions |
| step_number | INTEGER | Step number |
| step_status | VARCHAR(20) | DONE/ONGOING |
| idempotency_key | VARCHAR(100) | For duplicate detection (unique) |
| created_at | TIMESTAMP | Event time |

### Indexes for Performance

```sql
-- Fast session lookups
CREATE INDEX idx_session_id ON sessions(session_id);
CREATE INDEX idx_user_id ON sessions(user_id);
CREATE INDEX idx_status ON sessions(status);

-- Fast message retrieval
CREATE INDEX idx_message_session ON conversation_messages(session_uuid);
CREATE INDEX idx_message_timestamp ON conversation_messages(created_at);

-- Fast step lookups
CREATE INDEX idx_step_manual ON manual_steps(manual_uuid, step_number);

-- Idempotency checks
CREATE UNIQUE INDEX idx_idempotency ON progress_events(idempotency_key);
```

### Data Integrity Constraints

```python
# Foreign key constraints (CASCADE delete)
Session.manual_uuid → Manual.id
Message.session_uuid → Session.id
ManualStep.manual_uuid → Manual.id
ProgressEvent.session_uuid → Session.id

# Check constraints
current_step >= 1
current_step <= total_steps
total_steps >= 1
```

### My Schema Design Decisions

| Decision | Why I Made This Choice |
|----------|------------------------|
| **Separate ManualStep table** | To handle 2-100+ steps without schema changes or hardcoding |
| **UUID primary keys** | Better for distributed systems and avoids sequential ID guessing |
| **External IDs (manual_id, session_id)** | Lets clients provide their own identifiers |
| **`version` column in sessions** | Needed for optimistic locking to handle concurrent updates |
| **`idempotency_key` in progress_events** | Prevents duplicate processing when same update is sent twice |
| **Denormalized `total_steps` in Session** | Avoids JOIN on every progress check (performance trade-off) |
| **Timestamps with timezone** | Accurate duration tracking across timezones |
| **Indexes on foreign keys** | Optimized for common query patterns |

### Sample Manual Format

The schema supports manuals with anywhere from 2 to 100+ steps:

```json
{
  "manual_id": "manual-abc",
  "title": "Introduction to Python",
  "total_steps": 2,
  "steps": [
    {"step_number": 1, "title": "Hello, World!", "content": "Write a Python script..."},
    {"step_number": 2, "title": "Variables", "content": "Declare a variable..."}
  ]
}
```

The `manual_steps` table stores each step as a separate row, making it flexible to handle any number of steps

## API Design

### Design Philosophy

The API is structured around **resources** with **nested routes** for related operations. This approach provides:
- Clear URL hierarchy
- RESTful conventions
- Easy to understand and use

### Endpoint Structure

```
Sessions (core resource)
├── POST   /api/v1/sessions                    → Create session
├── GET    /api/v1/sessions                    → List sessions
├── GET    /api/v1/sessions/{id}               → Get session
├── PATCH  /api/v1/sessions/{id}               → Update session
├── DELETE /api/v1/sessions/{id}               → Delete session
├── POST   /api/v1/sessions/{id}/progress      → Submit progress (Type B/C)
├── GET    /api/v1/sessions/{id}/next-step     → Get next recommended step
└── GET    /api/v1/sessions/{id}/messages      → Get conversation history

Messages (linked to session)
└── POST   /api/v1/messages                    → Store chat message (Type A)

Manuals (reference data)
├── POST   /api/v1/manuals                     → Create manual
├── GET    /api/v1/manuals                     → List manuals
├── GET    /api/v1/manuals/{id}                → Get manual details
└── DELETE /api/v1/manuals/{id}                → Delete manual

Analytics (aggregated data)
├── GET    /api/v1/analytics/overview          → System statistics
├── GET    /api/v1/analytics/popular-manuals   → Most used manuals
└── GET    /api/v1/analytics/recent-activity   → Activity in last N hours
```

### Why I Chose Separate Endpoints

I decided to use **separate endpoints** for different input types instead of one combined endpoint:

| Decision | Reasoning |
|----------|-----------|
| **Nested routes** (`/sessions/{id}/progress`) | Progress belongs to a session - keeps related operations together |
| **Separate messages endpoint** | Messages can be created independently, just need session_id in body |
| **Dedicated `/next-step` endpoint** | Read-only operation, different from update |
| **Analytics as separate resource** | Aggregated data doesn't belong under sessions or manuals |

**Benefits:**
- **Single Responsibility**: Each endpoint has one clear purpose
- **Clear semantics**: Different HTTP methods and response formats
- **Better documentation**: Easier to understand in Swagger UI
- **Validation**: Different Pydantic schemas for each input type
- **Scalability**: Can scale message storage separately from progress tracking

---

## Input Data Handling

The service receives two types of input from upstream:

### Type A: Chat Messages

User messages from their interaction with the AI tutor.

```json
{
  "session_id": "session-456",
  "user_id": "user-123",
  "message": "I have completed the first step.",
  "sender": "user"
}
```

**Endpoint:** `POST /api/v1/messages`

**Processing:**
```
Validate → Store in database → Return with timestamp
```

### Type B & C: Progress Updates

Updates about what step the user is on and whether they're done or still working.

```json
{
  "session_id": "session-456",
  "user_id": "user-123",
  "current_step": 2,
  "step_status": "DONE"
}
```

**Status Values:**
- `DONE` - User finished this step, increment the counter
- `ONGOING` - User is still working, don't increment

**Endpoint:** `POST /api/v1/sessions/{session_id}/progress`

**Processing:**
```
├── Validate step bounds (not exceeding total_steps)
├── Check idempotency key (prevent duplicates)
├── If DONE → increment session.current_step
├── If final step → mark session as completed
├── Send webhook to external service
└── Return updated state with next step info
```

### Why I Used Separate Handling

| Aspect | Messages (Type A) | Progress (Type B/C) |
|--------|-------------------|---------------------|
| Data shape | `message` + `sender` | `current_step` + `step_status` |
| Processing | Simple store | Complex logic + webhook |
| Validation | Basic | Step bounds, idempotency |
| Side effects | None | Updates session, triggers webhook |

I considered using one combined endpoint but rejected it because mixing these would require complex conditional logic and make the API harder to understand and maintain

## Edge Cases

The service handles all 6 specified edge cases:

### Summary Table

| Edge Case | Detection | Response | HTTP Status |
|-----------|-----------|----------|-------------|
| Invalid step number | `step > total_steps` | Error message | 400 Bad Request |
| Duplicate update | `idempotency_key` exists | Return cached result | 200 OK (skip reprocess) |
| Out-of-order | `step < current_step` | Accept but don't regress | 200 OK |
| Session ended | `status != 'active'` | Error message | 400 Bad Request |
| Missing manual | `manual_id` not found | Error message | 404 Not Found |
| Concurrent update | Version mismatch | Retry message | 409 Conflict |

---

### 1. Invalid Step Numbers

**Scenario**: Upstream sends step 10 but manual only has 5 steps.

**Handling**:
```python
if progress.current_step > session.total_steps:
    raise InvalidStepError(
        f"Step {progress.current_step} exceeds total steps ({session.total_steps})"
    )
```

**Response**: HTTP 400 Bad Request
```json
{
  "error": "invalid_step",
  "message": "Step 10 exceeds total steps (5)",
  "session_id": "session-456"
}
```

---

### 2. Duplicate Updates

**Scenario**: Same progress update sent twice (network retry, client bug, etc.)

**Handling**: Use optional `idempotency_key` in progress updates.

```python
# Check if key already processed
if update.idempotency_key:
    existing = await db.query(ProgressEvent).filter(
        idempotency_key=update.idempotency_key
    ).first()
    if existing:
        return existing  # Return cached result, no reprocessing
```

**Response**: Returns original response, skips duplicate processing
```json
{
  "status": "already_processed",
  "original_result": { ... }
}
```

---

### 3. Out-of-Order Updates

**Scenario**: Step 3 arrives before step 2 (network delays, async processing)

**Handling**:
- Accept the update (log for audit trail)
- Only increment session progress forward, never regress
- Store in progress_events for audit

```python
if update.current_step >= session.current_step:
    session.current_step = update.current_step  # Move forward
else:
    logger.warning(f"Out-of-order: got step {update.current_step}, session on {session.current_step}")
    # Accept but don't regress session progress
```

**Response**: HTTP 200 OK (accepted but session not regressed)

---

### 4. Session Already Ended

**Scenario**: Progress update arrives after session is completed or ended.

**Handling**:
```python
if session.status in ['completed', 'ended']:
    raise SessionEndedError(
        f"Cannot update ended session {session.session_id}"
    )
```

**Response**: HTTP 400 Bad Request
```json
{
  "error": "session_ended",
  "message": "Session 'session-456' is already completed. Cannot accept updates.",
  "session_status": "completed"
}
```

---

### 5. Missing Manual

**Scenario**: Session creation references a manual_id that doesn't exist.

**Handling**:
```python
manual = await db.query(Manual).filter(manual_id=data.manual_id).first()
if not manual:
    raise ManualNotFoundError(f"Manual '{data.manual_id}' not found")
```

**Response**: HTTP 404 Not Found
```json
{
  "error": "manual_not_found",
  "message": "Manual 'invalid-manual' not found"
}
```

---

### 6. Concurrent Updates

**Scenario**: Multiple progress updates hit at the same time for the same session.

**Handling**: Optimistic locking with version column
```python
# Each session has a version column
class Session:
    version: Integer  # Incremented on each update

# Update with version check
result = await db.execute(
    update(Session)
    .where(Session.id == session.id)
    .where(Session.version == session.version)  # Optimistic lock
    .values(
        current_step=new_step,
        version=session.version + 1
    )
)

if result.rowcount == 0:
    raise ConcurrentUpdateError("Session was modified by another request")
```

**Response**: HTTP 409 Conflict
```json
{
  "error": "concurrent_update",
  "message": "Session was modified by another request. Please retry."
}
```

---

### Edge Case Flow Diagram

```
Progress Update Request
         │
         ▼
┌─────────────────────┐
│ Session exists?     │──No──→ 404 Not Found
└─────────────────────┘
         │ Yes
         ▼
┌─────────────────────┐
│ Session active?     │──No──→ 400 Session Ended
└─────────────────────┘
         │ Yes
         ▼
┌─────────────────────┐
│ Step valid?         │──No──→ 400 Invalid Step
│ (≤ total_steps)     │
└─────────────────────┘
         │ Yes
         ▼
┌─────────────────────┐
│ Duplicate key?      │──Yes─→ 200 Return Cached
└─────────────────────┘
         │ No
         ▼
┌─────────────────────┐
│ Version match?      │──No──→ 409 Retry
│ (concurrent check)  │
└─────────────────────┘
         │ Yes
         ▼
┌─────────────────────┐
│ Process Update      │
│ - Update step       │
│ - Send webhook      │
│ - Return success    │
└─────────────────────┘
```

## Feedback Mechanism

When a progress update is received with `step_status: "DONE"`:

1. **Update session** - Increment current_step counter
2. **Send webhook** - POST to external instruction delivery service
3. **Return response** - Include next step recommendation

### Webhook Payload

```json
{
    "event_type": "progress_update",
    "session_id": "session-456",
    "user_id": "user-123",
    "manual_id": "manual-abc",
    "previous_step": 1,
    "current_step": 2,
    "total_steps": 5,
    "step_status": "DONE",
    "session_status": "active",
    "session_duration_seconds": 125.5,
    "is_completed": false
}
```

### Event Types

- `session_created` - When a new session starts
- `progress_update` - When progress is updated
- `session_ended` - When a session completes or is abandoned

### Mock Webhook Server

The included mock server (`mock_webhook/`) simulates the external instruction delivery service:

- Receives and logs all webhooks
- View received webhooks: `GET http://localhost:8001/webhooks`
- Clear webhooks: `DELETE http://localhost:8001/webhooks`

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql+asyncpg://... | Database connection string |
| `WEBHOOK_URL` | http://mock_webhook:8001/webhook | External service URL |
| `WEBHOOK_ENABLED` | true | Enable/disable webhooks |
| `WEBHOOK_TIMEOUT` | 10 | Webhook timeout in seconds |
| `DEBUG` | false | Enable debug mode |

## Testing

### Run Tests

```bash
# Using Docker
docker-compose exec app pytest -v

# Locally (requires test dependencies)
pip install -r requirements.txt
pytest -v
```

### Test Coverage

```bash
pytest --cov=app --cov-report=html
```

### Test Categories

- `test_sessions.py` - Session CRUD operations
- `test_messages.py` - Conversation storage
- `test_progress.py` - Progress tracking
- `test_edge_cases.py` - All edge case scenarios

## API Documentation

### Swagger UI

Available at: `http://localhost:8000/docs`

### ReDoc

Available at: `http://localhost:8000/redoc`

### Example Requests

#### Create a Manual

```bash
curl -X POST http://localhost:8000/api/v1/manuals \
  -H "Content-Type: application/json" \
  -d '{
    "manual_id": "manual-abc",
    "title": "Introduction to Python",
    "steps": [
      {"step_number": 1, "title": "Hello, World!", "content": "Write a script that prints Hello, World!"},
      {"step_number": 2, "title": "Variables", "content": "Declare a variable and assign it a value."}
    ]
  }'
```

#### Create a Session

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-456",
    "user_id": "user-123",
    "manual_id": "manual-abc"
  }'
```

#### Submit Progress Update

```bash
curl -X POST http://localhost:8000/api/v1/sessions/session-456/progress \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "current_step": 1,
    "step_status": "DONE",
    "idempotency_key": "unique-key-123"
  }'
```

#### Add a Message

```bash
curl -X POST http://localhost:8000/api/v1/sessions/session-456/messages \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "message": "I have completed the first step.",
    "sender": "user"
  }'
```

## Assumptions

The following assumptions were made during development:

| Assumption | Details |
|------------|---------|
| **Authentication** | Handled upstream - all requests are assumed authenticated. No auth middleware in this service. |
| **User IDs** | String identifiers provided by the upstream system (not managed by this service) |
| **Session IDs** | Provided by the client in requests (not auto-generated by server) |
| **Manual Creation** | Manuals must be created before sessions can reference them |
| **Step Ordering** | Steps are completed sequentially (1 → 2 → 3), not randomly |
| **Webhook Delivery** | Best-effort with retry queue. Failed webhooks are queued and retried with exponential backoff |
| **Time Zones** | All timestamps stored in UTC. Duration calculated server-side |
| **Concurrency** | Moderate concurrent load expected. Optimistic locking handles race conditions |
| **Data Retention** | No automatic cleanup. Sessions and messages persist until explicitly deleted |
| **Manual Size** | Manuals can have 2-100+ steps. No upper limit enforced |

### Design Trade-offs I Made

| Decision | Trade-off | My Reasoning |
|----------|-----------|--------------|
| PostgreSQL over NoSQL | Less flexible schema, but ACID guarantees | Data integrity was more important than schema flexibility for this use case |
| Separate tables for steps | More JOINs, but flexible step counts | Worth it to support any number of steps without schema changes |
| Optimistic locking | Rare conflicts require retry | Better performance than pessimistic locking for expected load |
| Webhook retry queue | Added complexity | Needed to ensure feedback delivery even with temporary failures |
| Denormalized `total_steps` | Data duplication | Avoids JOIN on every progress check - acceptable trade-off |

## Project Structure

```
session-service/
├── app/                        # FastAPI Backend
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration settings
│   ├── database.py             # Database connection
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── api/routes/             # API endpoints
│   ├── services/               # Business logic
│   └── utils/                  # Utilities
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/         # Reusable components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API client
│   │   ├── App.tsx             # Main app component
│   │   └── main.tsx            # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
├── mock_webhook/               # Mock external service
├── tests/                      # Test suite
├── alembic/                    # Database migrations
├── docker-compose.yml          # All services
├── Dockerfile                  # Backend Dockerfile
├── postman_collection.json     # API demo
└── README.md
```

## License

MIT
