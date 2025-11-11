# models/ — Data Schemas and Type Definitions

## Purpose

This directory contains Pydantic models for request/response validation, type safety, and API documentation. All HTTP payloads are validated against these schemas.

---

## Directory Structure

```
models/
├── CLAUDE.md       # This file
├── schemas.py      # Pydantic models for API requests/responses
└── events.py       # Event type definitions (from Android app)
```

---

## schemas.py — API Request/Response Models

Defines all HTTP request bodies and response bodies using Pydantic.

### Benefits of Pydantic

1. **Automatic Validation**: Invalid requests rejected with 422 error
2. **Type Safety**: Type hints ensure correct data types
3. **Auto Documentation**: FastAPI generates OpenAPI schema
4. **Serialization**: Automatic JSON encoding/decoding
5. **Error Messages**: Clear validation error messages

### Common Patterns

#### Request Model

```python
from pydantic import BaseModel, Field

class EventStoreRequest(BaseModel):
    type: str = Field(..., min_length=1, description="Event type")
    data: dict = Field(default_factory=dict, description="Event data")
    timestamp: int = Field(default_factory=int, description="Unix timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "app_launch",
                "data": {"app": "instagram", "duration": 1200},
                "timestamp": 1699888888
            }
        }
```

#### Response Model

```python
class EventResponse(BaseModel):
    id: str = Field(..., description="Unique event ID")
    stored: bool = Field(..., description="Success flag")
    embedding_dim: int = Field(..., description="Embedding dimensions")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "event-abc123",
                "stored": True,
                "embedding_dim": 384
            }
        }
```

#### Error Model

```python
class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    status_code: int = Field(..., description="HTTP status code")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Event not found",
                "code": "NOT_FOUND",
                "status_code": 404
            }
        }
```

---

## Complete Schema Definitions

### Memory Store

```python
class MemoryStoreRequest(BaseModel):
    type: str
    data: dict = Field(default_factory=dict)
    timestamp: int = Field(default_factory=int)

class MemoryStoreResponse(BaseModel):
    id: str
    stored: bool
    embedding_dim: int
```

### Memory Search

```python
class SearchFilter(BaseModel):
    type: Optional[str] = None
    timestamp_min: Optional[int] = None
    timestamp_max: Optional[int] = None

class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=100)
    filters: Optional[SearchFilter] = None

class MemorySearchResult(BaseModel):
    id: str
    type: str
    data: dict
    timestamp: int
    similarity_score: float = Field(..., ge=0, le=1)

class MemorySearchResponse(BaseModel):
    results: list[MemorySearchResult]
    count: int
    total: int
```

### Memory Recent

```python
class MemoryRecentResponse(BaseModel):
    results: list[dict]
    count: int
    total: int
    has_more: bool
```

### State Management

```python
class MoodUpdateRequest(BaseModel):
    mood: str = Field(..., regex="^(happy|sad|focused|tired|anxious|neutral)$")
    context: Optional[str] = None

class MoodUpdateResponse(BaseModel):
    mood: str
    updated_at: int
    acknowledgement: str

class StateCurrentResponse(BaseModel):
    mood: str
    mood_updated_at: int
    thoughts: str
    thoughts_updated_at: int
    blog_posts: list[dict]

class BlogPost(BaseModel):
    title: str
    summary: Optional[str] = None
    url: str
    published_at: int
    scraped_at: Optional[int] = None

class StateBloglResponse(BaseModel):
    blog_posts: list[BlogPost]
    last_updated: int
    next_scrape: int
```

### Device Sync

```python
class SyncPullRequest(BaseModel):
    last_sync_timestamp: int = 0

class SyncContext(BaseModel):
    last_sync: int
    new_events_count: int
    server_time: int

class SyncPullResponse(BaseModel):
    current_state: dict
    recent_memories: list[dict]
    context: SyncContext

class SyncPushRequest(BaseModel):
    events: list[dict] = Field(min_items=1, max_items=100)

class SyncPushResult(BaseModel):
    event_index: int
    id: str
    success: bool
    error: Optional[str] = None

class SyncPushResponse(BaseModel):
    stored_count: int
    failed_count: int
    results: list[SyncPushResult]
```

### Authentication

```python
class TokenResponse(BaseModel):
    token: str = Field(..., description="JWT token")
    expires_in: int = Field(..., description="Seconds until expiration")
    token_type: str = Field("Bearer", description="Token type")

class RefreshTokenRequest(BaseModel):
    token: str = Field(..., description="Expired or valid JWT")

class RefreshTokenResponse(BaseModel):
    token: str
    expires_in: int
```

---

## events.py — Event Type Definitions

Sealed hierarchy of event types from the Android app.

### Event Types

```python
from typing import Union
from pydantic import BaseModel, Field

# Base event
class BaseEvent(BaseModel):
    type: str
    timestamp: int = Field(default_factory=int)
    device_id: str = Field(default="unknown")

# App events
class AppLaunchEvent(BaseEvent):
    type: str = Field("app_launch", const=True)
    data: dict = Field(default_factory=lambda: {"app": "", "duration": 0})

# Notification events
class NotificationEvent(BaseEvent):
    type: str = Field("notification", const=True)
    data: dict = Field(default_factory=lambda: {"source": "", "subject": ""})

# Mini-game events
class MiniGameCompleteEvent(BaseEvent):
    type: str = Field("minigame_complete", const=True)
    data: dict = Field(default_factory=lambda: {"game_type": "", "success": False})

# Union of all event types
AppEvent = Union[
    AppLaunchEvent,
    NotificationEvent,
    MiniGameCompleteEvent
]
```

### Event Registration

```python
# Mapping for easy lookup
EVENT_TYPES = {
    "app_launch": AppLaunchEvent,
    "notification": NotificationEvent,
    "minigame_complete": MiniGameCompleteEvent,
}

def create_event(type_str: str, data: dict, timestamp: int = None, device_id: str = "unknown") -> BaseEvent:
    """Factory for creating events by type"""
    event_class = EVENT_TYPES.get(type_str)
    if not event_class:
        raise ValueError(f"Unknown event type: {type_str}")

    return event_class(
        type=type_str,
        data=data,
        timestamp=timestamp or int(time.time()),
        device_id=device_id
    )
```

---

## Validation Examples

### Valid Request

```json
{
  "type": "app_launch",
  "data": {"app": "instagram", "duration": 1200},
  "timestamp": 1699888888
}
```

✅ Passes validation (all fields valid)

### Invalid Request (Wrong Type)

```json
{
  "type": "app_launch",
  "data": "not a dict",
  "timestamp": "not an int"
}
```

❌ Fails validation (data not dict, timestamp not int)

**Response**:
```json
{
  "detail": [
    {"loc": ["body", "data"], "msg": "value is not a valid dict"},
    {"loc": ["body", "timestamp"], "msg": "value is not a valid integer"}
  ]
}
```

### Invalid Mood

```json
{
  "mood": "angry"
}
```

❌ Fails validation ("angry" not in valid moods)

**Response**:
```json
{
  "detail": [
    {"loc": ["body", "mood"], "msg": "string does not match regex \"^(happy|sad|focused|tired|anxious|neutral)$\""}
  ]
}
```

---

## Field Types

### Common Fields

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `id` | `str` | Unique identifier | `"event-abc123"` |
| `type` | `str` | Event/resource type | `"app_launch"` |
| `timestamp` | `int` | Unix timestamp | `1699888888` |
| `data` | `dict` | Event payload | `{"app": "instagram"}` |
| `status` | `str` | Status/state | `"success"`, `"pending"` |
| `score` | `float` | Similarity/confidence | `0.92` |

### Constraints

```python
# String constraints
name: str = Field(..., min_length=1, max_length=100)

# Integer constraints
count: int = Field(..., ge=0, le=100)  # >= 0, <= 100

# Float constraints
score: float = Field(..., ge=0.0, le=1.0)

# Enum-like constraints
mood: str = Field(..., regex="^(happy|sad|focused|tired|anxious|neutral)$")

# Optional fields
context: Optional[str] = None

# Default values
limit: int = 20
offset: int = 0

# Required fields
query: str = Field(...)
```

---

## Auto-Generated Documentation

FastAPI automatically generates OpenAPI spec from Pydantic models:

**Access at**:
- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/redoc` — ReDoc
- `http://localhost:8000/openapi.json` — Raw OpenAPI

**Example Generated Endpoint**:
```
POST /api/memory/store
Request Body: EventStoreRequest
Response: EventResponse (201)
Responses: ErrorResponse (400, 401, 422, 500)
```

---

## Testing with Pydantic

```python
# Valid construction
event = MemoryStoreRequest(
    type="app_launch",
    data={"app": "instagram"},
    timestamp=1699888888
)
assert event.type == "app_launch"

# Validation error
try:
    event = MemoryStoreRequest(
        type="app_launch",
        data="invalid",  # Should be dict
        timestamp=1699888888
    )
except ValidationError as e:
    assert "data" in str(e)

# JSON serialization
json_str = event.model_dump_json()
parsed = MemoryStoreRequest.model_validate_json(json_str)
assert parsed == event
```

---

## Best Practices

### ✅ DO

- **Define all request/response models** in this file
- **Use Field() for constraints** (min_length, regex, ge, le)
- **Provide examples** in Config.json_schema_extra
- **Make required fields explicit** with Field(...)
- **Use Optional[T]** for truly optional fields
- **Document fields** with description parameter
- **Validate enums** with regex or enum fields

### ❌ DON'T

- **Accept raw dict** without schema validation
- **Skip error handling** in routes
- **Change field names** without migration plan
- **Use str for everything** (type hints are valuable)
- **Mix validation logic** into routes (use Pydantic)

---

## Migration Strategy

If you need to change a schema (add/remove fields):

**Old Schema**:
```python
class EventRequest(BaseModel):
    type: str
    data: dict
```

**New Schema** (backwards compatible):
```python
class EventRequest(BaseModel):
    type: str
    data: dict
    source: Optional[str] = None  # New field, optional
```

**Breaking Change** (not recommended):
```python
# Old route still works
@router.post("/api/memory/store")
async def store_event_v1(event: EventRequestV1):
    ...

# New route for new schema
@router.post("/api/v2/memory/store")
async def store_event_v2(event: EventRequestV2):
    ...
```

---

See related files:
- `CLAUDE.md` — Backend overview
- `../api/routes/CLAUDE.md` — Routes that use these schemas
- `../services/CLAUDE.md` — Services that work with schemas
