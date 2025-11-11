# api/routes/ — Endpoint Definitions

## Purpose

This directory contains the actual HTTP endpoint handlers organized by domain. Each module handles a specific subset of functionality.

---

## Directory Structure

```
routes/
├── CLAUDE.md      # This file
├── memory.py      # Long-term memory endpoints (Chroma)
├── state.py       # Short-term state endpoints (text files)
└── sync.py        # Device sync endpoints (combined)
```

---

## memory.py — Long-Term Memory Endpoints

Provides semantic search and storage of events in Chroma.

### POST /api/memory/store

**Purpose**: Store a new event with embedding

**Request**:
```json
{
  "type": "app_launch",
  "data": {
    "app": "instagram",
    "duration_seconds": 1200
  },
  "timestamp": 1699888888
}
```

**Response** (201 Created):
```json
{
  "id": "event-abc123",
  "stored": true,
  "embedding_dim": 384
}
```

**Implementation Notes**:
- Extracts `type` and `data` fields
- Generates text representation for embedding
- Calls `vector_store.insert(event)` service
- Returns event ID and confirmation

---

### POST /api/memory/search

**Purpose**: Semantic search over stored events

**Request**:
```json
{
  "query": "when did i use instagram",
  "limit": 10,
  "filters": {
    "type": "app_launch"
  }
}
```

**Response** (200 OK):
```json
{
  "results": [
    {
      "id": "event-abc123",
      "type": "app_launch",
      "data": {"app": "instagram", "duration_seconds": 1200},
      "timestamp": 1699888888,
      "similarity_score": 0.92
    }
  ],
  "count": 1,
  "total": 5
}
```

**Implementation Notes**:
- Query is converted to embedding
- Chroma searches by cosine similarity
- Optional filters on event type
- Returns sorted by similarity score

---

### GET /api/memory/recent

**Purpose**: Get recent events without semantic search

**Request**:
```
GET /api/memory/recent?limit=20&offset=0&type=app_launch
```

**Response** (200 OK):
```json
{
  "results": [
    {
      "id": "event-abc123",
      "type": "app_launch",
      "data": {"app": "instagram"},
      "timestamp": 1699888888
    }
  ],
  "count": 1,
  "total": 50,
  "has_more": true
}
```

**Implementation Notes**:
- Pagination: `limit` (default 20), `offset` (default 0)
- Optional `type` filter
- Results sorted by timestamp (newest first)
- `has_more` indicates if more results available

---

### DELETE /api/memory/{event_id}

**Purpose**: Remove a stored event (cleanup)

**Response** (204 No Content):
```
(empty body, just status code)
```

**Error** (404 Not Found):
```json
{
  "error": "Event not found"
}
```

**Implementation Notes**:
- Validates event exists
- Removes from Chroma
- Optional: Archive instead of delete
- Used for data cleanup/privacy

---

## state.py — Current State Endpoints

Manages short-term memory (mood, thoughts, blog summaries).

### GET /api/state/current

**Purpose**: Get current mood, thoughts, and context

**Response** (200 OK):
```json
{
  "mood": "focused",
  "mood_updated_at": 1699888888,
  "thoughts": "Working on backend architecture. Feeling productive and organized.",
  "thoughts_updated_at": 1699887777,
  "blog_posts": [
    {
      "title": "Backend Design Patterns",
      "summary": "Discussed FastAPI architecture and service layers",
      "url": "https://your-blog.com/backend-design",
      "published_at": 1699886666
    }
  ]
}
```

**Implementation Notes**:
- Reads from text files:
  - `current_mood.txt` → mood value
  - `recent_thoughts.txt` → thoughts summary
  - `blog_cache.json` → parsed blog posts
- Each field has update timestamp
- Blog posts sorted by date (newest first)

---

### POST /api/state/update

**Purpose**: Update current mood from phone

**Request**:
```json
{
  "mood": "tired",
  "context": "Just finished a long meeting"
}
```

**Response** (200 OK):
```json
{
  "mood": "tired",
  "updated_at": 1699888888,
  "acknowledgement": "Mood updated"
}
```

**Implementation Notes**:
- Validates mood is from predefined list
- Updates `current_mood.txt`
- Optional context for AI insights
- Returns confirmation with timestamp

---

### GET /api/state/blog

**Purpose**: Get cached blog summaries

**Response** (200 OK):
```json
{
  "blog_posts": [
    {
      "title": "Building Home Servers",
      "summary": "Guide to setting up a privacy-focused home server",
      "url": "https://your-blog.com/home-servers",
      "published_at": 1699886666,
      "scraped_at": 1699800000
    }
  ],
  "last_updated": 1699800000,
  "next_scrape": 1699813600
}
```

**Implementation Notes**:
- Reads from `blog_cache.json`
- Returns cached results (no live scraping)
- Background task updates periodically
- Shows when next scrape is scheduled

---

## sync.py — Device Sync Endpoints

High-level endpoints combining memory and state for efficient syncing.

### POST /api/sync/pull

**Purpose**: Complete state sync for phone (memory + current state + context)

**Request**:
```json
{
  "last_sync_timestamp": 1699777777
}
```

**Response** (200 OK):
```json
{
  "current_state": {
    "mood": "focused",
    "thoughts": "Working on features",
    "blog_posts": [...]
  },
  "recent_memories": [
    {
      "id": "event-abc123",
      "type": "app_launch",
      "data": {"app": "instagram"},
      "timestamp": 1699888888
    }
  ],
  "context": {
    "last_sync": 1699777777,
    "new_events_count": 5,
    "server_time": 1699888888
  }
}
```

**Implementation Notes**:
- Retrieves current state (mood, thoughts, blog)
- Fetches events since `last_sync_timestamp`
- Combines into single response
- Used by phone on app startup or periodic sync
- Phone uses data to prime AI context

---

### POST /api/sync/push

**Purpose**: Batch send events from phone to server

**Request**:
```json
{
  "events": [
    {
      "type": "app_launch",
      "data": {"app": "instagram", "duration_seconds": 1200},
      "timestamp": 1699888888
    },
    {
      "type": "notification",
      "data": {"source": "gmail", "subject": "Important email"},
      "timestamp": 1699888900
    }
  ]
}
```

**Response** (201 Created):
```json
{
  "stored_count": 2,
  "failed_count": 0,
  "results": [
    {"event_index": 0, "id": "event-abc123", "success": true},
    {"event_index": 1, "id": "event-def456", "success": true}
  ]
}
```

**Implementation Notes**:
- Validates each event individually
- Stores all valid events
- Returns success/failure for each
- Partial success allowed (some events fail, others succeed)
- Used for efficient batch uploads from phone

---

## Common Patterns

### Pagination

Applied to list endpoints:
```
GET /api/memory/recent?limit=20&offset=40
```

**Query Parameters**:
- `limit` — Results per page (default 20, max 100)
- `offset` — Skip first N results (default 0)

**Response**:
```json
{
  "results": [...],
  "count": 20,
  "total": 100,
  "has_more": true
}
```

### Filtering

Applied to memory search:
```
POST /api/memory/search with filters
```

**Example Filters**:
```json
{
  "filters": {
    "type": "app_launch",
    "timestamp_min": 1699777777,
    "timestamp_max": 1699888888
  }
}
```

### Error Handling

All endpoints return consistent error format:

```json
{
  "detail": "Event not found",
  "code": "NOT_FOUND",
  "status_code": 404
}
```

---

## Rate Limiting

Applied globally by security middleware:
- **Per device**: 100 requests/minute
- **Shared pool**: 1000 requests/minute per server
- **Response**: 429 Too Many Requests

**Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1699888888
```

---

## Notes for Implementation

### memory.py
- Use `vector_store.insert()`, `search()`, `delete()`
- Generate embeddings automatically on insert
- Handle embedding failures gracefully
- Index updates are immediate

### state.py
- Read/write text files atomically
- Validate mood from predefined list
- Include timestamps with all data
- Handle file not found (return defaults)

### sync.py
- Combine memory and state efficiently
- Use `last_sync_timestamp` to avoid duplicate data
- Return minimal payload for mobile efficiency
- Handle partial failures in batch operations

---

See related files:
- `../CLAUDE.md` — API layer overview
- `../middleware/CLAUDE.md` — Auth/security
- `../../services/CLAUDE.md` — Service layer
- `../../models/CLAUDE.md` — Request/response schemas
