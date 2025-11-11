# api/ — HTTP API Layer

## Purpose

The `api/` directory contains all HTTP endpoint definitions and middleware for authentication/security. It provides the interface between the Android app and backend services.

---

## Directory Structure

```
api/
├── CLAUDE.md              # This file
├── routes/                # API endpoint definitions
│   ├── CLAUDE.md          # Routes overview
│   ├── memory.py          # POST/GET /api/memory/*
│   ├── state.py           # POST/GET /api/state/*
│   └── sync.py            # POST /api/sync/*
└── middleware/            # Authentication, security, logging
    ├── CLAUDE.md          # Middleware overview
    ├── auth.py            # JWT validation
    └── security.py        # Rate limiting, CORS
```

---

## Design Principles

### 1. Stateless Routes

Routes **never hold state**. They:
- Receive request → Validate with Pydantic → Call service → Return response
- All state is in Chroma or text files
- No in-memory caches or instance variables

### 2. Dependency Injection

Routes receive services via FastAPI's dependency system:
```python
from fastapi import APIRouter, Depends
from app.services.vector_store import VectorStore

router = APIRouter()

async def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store

@router.post("/memory/store")
async def store_event(
    event: EventSchema,
    vector_store: VectorStore = Depends(get_vector_store)
):
    await vector_store.insert(event)
```

### 3. Type Safety

All requests/responses use Pydantic models:
```python
from pydantic import BaseModel, Field

class EventSchema(BaseModel):
    type: str = Field(..., description="Event type")
    data: dict = Field(default_factory=dict)
    timestamp: int = Field(default_factory=int)

class EventResponse(BaseModel):
    id: str
    stored: bool
```

---

## Route Structure

### `/api/memory/*` — Long-Term Memory (Chroma)

Semantic search and storage of events with embeddings.

**Endpoints** (see `routes/memory.py`):
- `POST /api/memory/store` — Store new event
- `POST /api/memory/search` — Search by semantic similarity
- `GET /api/memory/recent` — Get recent events (no search)
- `DELETE /api/memory/{event_id}` — Remove event

### `/api/state/*` — Current State (Text Files)

Get/update mood, thoughts, context.

**Endpoints** (see `routes/state.py`):
- `GET /api/state/current` — Get current mood + thoughts
- `POST /api/state/update` — Update mood from phone
- `GET /api/state/blog` — Get latest blog summaries

### `/api/sync/*` — Device Sync

Full sync operations combining memory + state.

**Endpoints** (see `routes/sync.py`):
- `POST /api/sync/pull` — Get complete current state + memory context
- `POST /api/sync/push` — Send batch of events from phone

---

## Common Request/Response Pattern

**Request** (from Android):
```json
{
  "Authorization": "Bearer <JWT_TOKEN>",
  "Content-Type": "application/json"
}
```

**Response** (from Backend):
```json
{
  "status": "success",
  "data": { ... },
  "timestamp": 1699999999,
  "error": null
}
```

**Error Response**:
```json
{
  "status": "error",
  "data": null,
  "timestamp": 1699999999,
  "error": {
    "code": "INVALID_TOKEN",
    "message": "JWT token has expired"
  }
}
```

---

## Middleware Chain

### JWT Authentication Middleware

**Purpose**: Validate JWT token on all protected routes

**Skips** (public endpoints):
- `GET /api/health`
- `GET /docs`
- `GET /redoc`
- `POST /api/auth/token` (initial setup only)

**On Valid Token**:
- Extract device ID from token
- Inject into request context for logging
- Proceed to route handler

**On Invalid Token**:
- Return 401 Unauthorized
- No further processing

### Security Middleware

**Purpose**: Rate limiting, CORS, header validation

**Features**:
- Rate limit: 100 requests/minute per device
- CORS: Only allow from your app's domain
- Security headers: X-Content-Type-Options, X-Frame-Options

**Bypass**:
- Cloudflare handles most CORS (tunnel handles origin)
- Rate limiting per device ID (from JWT)

### Logging Middleware

**Purpose**: Structured logging of all requests

**Logs**:
- Request: method, path, device_id, query_params
- Response: status_code, response_time, bytes_sent
- Errors: full stack trace (except password fields)

**Example Log**:
```
2024-01-15 14:23:45 | INFO | POST /api/memory/store | device_id=device-001 | status=201 | duration=45ms
```

---

## Error Handling

All routes should handle errors gracefully:

```python
@router.post("/memory/store")
async def store_event(
    event: EventSchema,
    vector_store: VectorStore = Depends(get_vector_store)
):
    try:
        event_id = await vector_store.insert(event)
        return EventResponse(id=event_id, stored=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

**Status Codes**:
- 200 OK — Request successful
- 201 Created — Resource created
- 400 Bad Request — Invalid input (Pydantic validation)
- 401 Unauthorized — Missing/invalid JWT
- 403 Forbidden — Permission denied
- 404 Not Found — Resource not found
- 429 Too Many Requests — Rate limited
- 500 Internal Server Error — Unexpected error

---

## Authentication Flow

### Initial Setup (One-time)

```
1. Admin calls: POST /api/auth/token with admin_secret
2. Backend generates JWT for device (e.g., device-001)
3. Token returned: {"token": "eyJhbGc...", "expires_in": 86400}
4. Admin stores token securely on phone
```

### Each Request

```
1. Phone includes: Authorization: Bearer <token>
2. Auth middleware validates JWT signature
3. If valid: Extract device_id, continue to handler
4. If invalid/expired: Return 401, client refreshes token
```

### Token Refresh

```
1. Phone calls: POST /api/auth/refresh with expired token
2. Backend validates old token (ignoring expiry)
3. If signature valid: Generate new token
4. Return new token: {"token": "eyJhbGc...", "expires_in": 86400}
```

---

## Testing Routes

**Using curl**:
```bash
# Health check (no auth)
curl http://localhost:8000/api/health

# Store event (with JWT)
curl -X POST http://localhost:8000/api/memory/store \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "app_launch", "data": {"app": "instagram"}}'

# Get current state
curl http://localhost:8000/api/state/current \
  -H "Authorization: Bearer $TOKEN"
```

**Using Python httpx**:
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/memory/store",
        headers={"Authorization": f"Bearer {token}"},
        json={"type": "app_launch", "data": {"app": "instagram"}}
    )
    print(response.json())
```

---

## Notes for Implementation

- **Keep routes thin**: Business logic belongs in services
- **Validate early**: Use Pydantic models to catch errors
- **Document endpoints**: Add docstrings and OpenAPI descriptions
- **Test each route**: Unit tests for all endpoints
- **Handle timeouts**: Set reasonable timeouts for service calls
- **Log errors**: Always log exceptions for debugging

---

See related files:
- `routes/CLAUDE.md` — Detailed endpoint definitions
- `middleware/CLAUDE.md` — Auth and security details
- `../services/CLAUDE.md` — Business logic layer
- `../models/CLAUDE.md` — Request/response schemas
