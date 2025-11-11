# Flanergide Backend — Architecture Overview

## Purpose

The Flanergide backend is a secure, privacy-focused server that provides persistent memory and contextual awareness for the Android app. It runs on a home server and enables:

1. **Long-term memory** via vector embeddings stored in Chroma
2. **Short-term context** via text file summaries of mood, thoughts, and recent blog posts
3. **Secure device-to-server communication** via Cloudflare Tunnel + JWT

---

## High-Level Architecture

```
Android Phone ─── Cloudflare Tunnel ──> Home Server (Backend)
   (FastAPI client)     (no port forwarding)    (FastAPI + Chroma)
                                   │
                                   ├─> Chroma (vector DB)
                                   │
                                   ├─> Text Files (short-term memory)
                                   │
                                   └─> Blog Scraper (background task)
```

### Key Design Principles

1. **Privacy-First**: All data stays on your home server, no cloud services
2. **Vector-Based Memory**: Semantic search over long-term events and interactions
3. **Dual Memory System**:
   - Long-term: Vector DB for searchable history
   - Short-term: Text files for current state (mood, thoughts)
4. **Secure by Default**: Cloudflare Tunnel hides home server IP, JWT validates requests
5. **Minimal Footprint**: Simple, stateless FastAPI design; Chroma handles persistence

---

## Core Components

### 1. FastAPI Application (`app/`)
Main entry point, dependency injection, configuration management.

**Responsibilities**:
- Initialize FastAPI app with middleware
- Set up Chroma connection
- Load configuration from `.env`
- Define exception handlers and logging

**See**: `app/CLAUDE.md`

---

### 2. API Routes (`app/api/routes/`)
HTTP endpoints for phone-to-server communication.

**Endpoints**:
- **memory.py**: Store/search long-term events
- **state.py**: Get/update current mood and context
- **sync.py**: Sync phone data, retrieve AI context

**See**: `app/api/routes/CLAUDE.md`

---

### 3. Middleware (`app/api/middleware/`)
Authentication, authorization, and security.

**Components**:
- **auth.py**: JWT token validation
- **security.py**: Rate limiting, CORS, request validation

**See**: `app/api/middleware/CLAUDE.md`

---

### 4. Services (`app/services/`)
Business logic and integration layer.

**Services**:
- **vector_store.py**: Chroma operations (insert, search, delete)
- **blog_scraper.py**: Fetch and parse blog HTML
- **summarizer.py**: AI-powered text summarization
- **state_manager.py**: Manage mood and context text files

**See**: `app/services/CLAUDE.md`

---

### 5. Models (`app/models/`)
Pydantic schemas for request/response validation.

**Schemas**:
- **schemas.py**: API request/response models
- **events.py**: Event types from Android app

**See**: `app/models/CLAUDE.md`

---

### 6. Storage (`app/storage/`)
Persistence layer for Chroma and text files.

**Directories**:
- **chroma_db/**: Chroma database files
- **state/**: Current mood/thoughts text files

**See**: `app/storage/CLAUDE.md`

---

## Data Flow Examples

### Example 1: Phone Sends an Event (Store in Long-Term Memory)

```
1. Android app emits event (e.g., "User opened Instagram at 3pm")
2. Phone sends POST /api/memory/store with JWT token
3. Middleware validates JWT
4. memory.py route receives request
5. vector_store service generates embedding
6. Chroma stores event with metadata
7. Response: {"id": "event-123", "stored": true}
```

---

### Example 2: Phone Requests Current State

```
1. Android app calls GET /api/state/current with JWT
2. Middleware validates token
3. state.py route calls state_manager service
4. state_manager reads current_mood.txt and recent_thoughts.txt
5. Response: { "mood": "focused", "thoughts": "Working on features", "blog_posts": [...] }
```

---

### Example 3: Blog Scraper Updates Short-Term Memory

```
1. Background task triggers (e.g., every 4 hours)
2. blog_scraper fetches HTML from your blog URL
3. Parses text using BeautifulSoup
4. Sends text to summarizer (AI)
5. AI returns summary of latest thoughts
6. state_manager updates recent_thoughts.txt
7. Next phone sync gets updated content
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI | HTTP API, dependency injection |
| **Vector DB** | Chroma | Semantic search over long-term memory |
| **Authentication** | JWT (PyJWT) | Secure device-to-server communication |
| **Web Scraping** | BeautifulSoup4, httpx | Blog content extraction |
| **Summarization** | OpenAI API (or local LLM) | AI text summarization |
| **Async** | asyncio, ASGI | Non-blocking I/O |
| **Config** | python-dotenv | Environment variables |
| **Reverse Proxy** | Cloudflare Tunnel | Secure NAT traversal, no port forwarding |

---

## Security Model

### Cloudflare Tunnel

**Why**: Hide your home server's IP, prevent direct access, enforce HTTPS

**Setup**:
```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Authenticate and create tunnel
cloudflared tunnel login
cloudflared tunnel create flanergide

# Route to local FastAPI
cloudflared tunnel route dns flanergide your-domain.com
cloudflared tunnel run flanergide

# Or use config file: cloudflared-config.yml
```

**Result**: `https://flanergide.your-domain.com` → `localhost:8000`

### JWT Authentication

**Flow**:
1. One-time setup: Generate JWT secret, create initial device token
2. Each request from phone includes `Authorization: Bearer <token>`
3. Middleware verifies token signature and expiration
4. Expired tokens can be refreshed via `/api/auth/refresh`

**Token Format**:
```json
{
  "sub": "device-001",
  "device_name": "Pixel 7",
  "exp": 1699999999,
  "iat": 1699888888
}
```

### Additional Security

- **Input Validation**: Pydantic models validate all requests
- **Rate Limiting**: Prevent brute force or abuse
- **CORS**: Only allow requests from your app
- **HTTPS Enforced**: Cloudflare tunnel handles TLS

---

## Development Workflow

### 1. Setup (One-time)

```bash
cd backend/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure `.env`

```
CLOUDFLARE_TUNNEL_URL=https://flanergide.your-domain.com
JWT_SECRET=<generate-with-secrets.token_hex(32)>
BLOG_URL=https://your-blog.com
OPENAI_API_KEY=<your-key>
```

### 3. Run Locally

```bash
# Terminal 1: FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Cloudflare Tunnel
cloudflared tunnel run flanergide

# Terminal 3: Verify
curl https://flanergide.your-domain.com/api/health
```

### 4. Deploy to Home Server

- Copy project to home server (or git clone)
- Set up systemd service or Docker container
- Configure tunnel credentials
- Ensure Chroma persistence directory exists

---

## File Structure

```
backend/
├── CLAUDE.md                  # This file
├── app/
│   ├── CLAUDE.md              # App layer overview
│   ├── main.py                # FastAPI entry point
│   ├── config.py              # Configuration / env vars
│   ├── api/
│   │   ├── CLAUDE.md          # API layer overview
│   │   ├── routes/
│   │   │   ├── CLAUDE.md      # Routes overview
│   │   │   ├── memory.py      # POST/GET /api/memory/*
│   │   │   ├── state.py       # POST/GET /api/state/*
│   │   │   └── sync.py        # POST /api/sync/*
│   │   └── middleware/
│   │       ├── CLAUDE.md      # Middleware overview
│   │       ├── auth.py        # JWT validation
│   │       └── security.py    # Rate limiting, CORS
│   ├── services/
│   │   ├── CLAUDE.md          # Services overview
│   │   ├── vector_store.py    # Chroma operations
│   │   ├── blog_scraper.py    # Blog fetching
│   │   ├── summarizer.py      # AI summarization
│   │   └── state_manager.py   # Text file management
│   ├── models/
│   │   ├── CLAUDE.md          # Models overview
│   │   ├── schemas.py         # Pydantic models
│   │   └── events.py          # Event types
│   └── storage/
│       ├── CLAUDE.md          # Storage overview
│       ├── chroma_db/         # Chroma files (gitignored)
│       └── state/             # Text files (gitignored)
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── .gitignore                 # Ignore .env, chroma_db, state/
├── docker-compose.yml         # Optional Docker setup
└── cloudflared-config.yml     # Cloudflare Tunnel config
```

---

## Module Communication Rules

### ✅ DO

- Routes call services, never directly manipulate storage
- Services are stateless functions operating on Chroma/files
- Middleware runs on all routes (auth, rate limiting)
- Configuration comes from `.env` and `config.py` only
- Async/await for all I/O operations

### ❌ DON'T

- Direct database manipulation from routes
- Hardcoded secrets anywhere in code
- Synchronous I/O in FastAPI routes
- Skip JWT validation on any endpoint
- Expose internal error details to client

---

## Integration with Android App

The Android app (Flanergide) integrates with this backend:

1. **On startup**: Phone requests `/api/state/current` to get mood/context
2. **On events**: Phone sends `/api/memory/store` with app usage data
3. **Periodically**: Phone syncs with `/api/sync/pull` to get AI insights
4. **On response**: Phone receives summarized blog posts and mood analysis

**See**: `../android/app/src/main/java/com/realityskin/backend/` (future)

---

## Next Steps

1. Implement `requirements.txt` with all dependencies
2. Create `.env.example` template
3. Implement `app/main.py` (FastAPI init)
4. Implement each service (Chroma, blog scraper, etc.)
5. Implement API routes
6. Add middleware (JWT, rate limiting)
7. Set up Cloudflare Tunnel on home server
8. Test phone-to-server communication
9. Deploy and monitor

---

## Notes for AI Agent

- **Always validate input**: Use Pydantic models for all requests
- **Keep services stateless**: They transform data, don't hold state
- **Use async/await**: FastAPI expects async route handlers
- **Log everything**: Add structured logging for debugging
- **Test security**: JWT validation, rate limiting, CORS
- **Document API**: OpenAPI/Swagger available at `/docs`

---

**Target Users**: Technical users who host their own servers, value privacy
**Deployment**: Home server (Linux/Mac/Windows with Python 3.9+)
**Database**: Chroma (embedded, no separate server needed)
**Reverse Proxy**: Cloudflare Tunnel (no port forwarding required)
