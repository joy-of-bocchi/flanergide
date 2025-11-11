# app/ — FastAPI Application Layer

## Purpose

The `app/` directory contains the core FastAPI application initialization, configuration, and dependency management. It serves as the foundation for all API routes and services.

---

## Directory Structure

```
app/
├── CLAUDE.md              # This file
├── main.py                # FastAPI app instance, middleware setup
├── config.py              # Configuration loading from .env
├── api/                   # API routes and middleware (see api/CLAUDE.md)
├── services/              # Business logic (see services/CLAUDE.md)
├── models/                # Pydantic schemas (see models/CLAUDE.md)
└── storage/               # Persistence layer (see storage/CLAUDE.md)
```

---

## Core Files

### main.py — FastAPI Entry Point

**Responsibilities**:
1. Create FastAPI app instance
2. Load configuration
3. Initialize global dependencies (Chroma, services)
4. Register middleware (JWT auth, rate limiting, CORS)
5. Include API routers
6. Define health check endpoint

**Structure**:
```python
from fastapi import FastAPI
from app.config import settings
from app.api.routes import memory, state, sync
from app.api.middleware import auth, security
from app.services.vector_store import VectorStore
from app.services.state_manager import StateManager

app = FastAPI(
    title="Flanergide Backend",
    description="Secure home server backend for personal AI",
    version="0.1.0"
)

# Initialize global services
@app.on_event("startup")
async def startup():
    # Initialize Chroma connection
    # Initialize state files
    # Load configuration
    pass

# Register middleware (order matters!)
app.add_middleware(SecurityMiddleware)      # Rate limiting, CORS
app.add_middleware(AuthMiddleware)          # JWT validation
app.add_middleware(LoggingMiddleware)       # Request logging

# Include routers
app.include_router(memory.router)
app.include_router(state.router)
app.include_router(sync.router)

# Health check
@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

**Key Points**:
- Middleware registration order: outer → inner (bottom → top in request flow)
- Startup events initialize persistent services (Chroma connection)
- Routers are separated by domain (memory, state, sync)

---

### config.py — Configuration Management

**Responsibilities**:
1. Load environment variables from `.env`
2. Provide type-safe configuration access
3. Validate required settings on startup
4. Define defaults where appropriate

**Structure**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # Security
    JWT_SECRET: str  # Required
    JWT_ALGORITHM: str = "HS256"
    TOKEN_EXPIRY_HOURS: int = 24

    # Cloudflare Tunnel
    CLOUDFLARE_TUNNEL_URL: str  # Required

    # Services
    BLOG_URL: str  # Required
    OPENAI_API_KEY: str  # Required
    CHROMA_PERSIST_DIR: str = "./app/storage/chroma_db"
    STATE_DIR: str = "./app/storage/state"

    # Feature flags
    ENABLE_BLOG_SCRAPER: bool = True
    BLOG_SCRAPER_INTERVAL_HOURS: int = 4
    ENABLE_RATE_LIMITING: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**Key Points**:
- Uses Pydantic for validation and type safety
- Required settings will fail on startup if missing
- Defaults provided for optional settings
- Loaded from `.env` file

---

## Startup Flow

When the FastAPI app starts:

```
1. config.py loads .env and validates all settings
2. main.py startup event triggers:
   - Chroma connection initialized (persistent dir created if needed)
   - State files directory created if needed
   - Blog scraper scheduled (if enabled)
   - Services instantiated and stored as app.state
3. Middleware chains registered
4. Routers included
5. App ready to receive requests
```

---

## Dependency Injection

FastAPI provides global and per-request dependency injection:

**Global Dependencies** (app.state):
```python
@app.on_event("startup")
async def startup():
    app.state.vector_store = VectorStore(settings.CHROMA_PERSIST_DIR)
    app.state.state_manager = StateManager(settings.STATE_DIR)
    app.state.blog_scraper = BlogScraper(settings.BLOG_URL)
```

**Per-Request Dependencies**:
```python
# In routes
from fastapi import Depends, Request

async def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store

@router.post("/memory/store")
async def store_event(
    event: EventSchema,
    vector_store: VectorStore = Depends(get_vector_store)
):
    # Use vector_store
    pass
```

---

## Middleware Stack

Middleware runs in **reverse registration order**:

1. **Logger Middleware** (outermost) — Logs all requests/responses
2. **Security Middleware** — Rate limiting, CORS headers
3. **Auth Middleware** — JWT validation (skips `/api/health`, `/docs`)
4. **Route Handler** (innermost) — Your endpoint logic

**Request Flow** (top to bottom):
```
Request → Logger → Security → Auth → Route Handler → Response
Response ← Logger ← Security ← Auth ← Route Handler
```

---

## Error Handling

FastAPI provides automatic exception handling:

```python
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

**Status Codes**:
- 200: Success
- 400: Bad request (invalid input)
- 401: Unauthorized (missing/invalid JWT)
- 429: Too many requests (rate limited)
- 500: Server error

---

## Testing the App

**Health Check** (no auth required):
```bash
curl http://localhost:8000/api/health
# Response: {"status": "ok"}
```

**API Documentation** (auto-generated by FastAPI):
```bash
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

**With JWT Token** (all other endpoints):
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/state/current
```

---

## Environment Variables (`.env`)

Required for startup:
- `JWT_SECRET` — Generated with `secrets.token_hex(32)`
- `CLOUDFLARE_TUNNEL_URL` — Your tunnel URL
- `BLOG_URL` — Your blog homepage
- `OPENAI_API_KEY` — For summarization

Optional (with defaults):
- `SERVER_HOST` — Default: `0.0.0.0`
- `SERVER_PORT` — Default: `8000`
- `CHROMA_PERSIST_DIR` — Default: `./app/storage/chroma_db`
- `STATE_DIR` — Default: `./app/storage/state`
- `BLOG_SCRAPER_INTERVAL_HOURS` — Default: `4`

See `.env.example` for template.

---

## Notes for Implementation

- **Async all the way**: All endpoints should be `async def`, use `await`
- **No blocking I/O**: Use httpx for HTTP, not requests
- **Startup validation**: Check that required files/dirs exist
- **Graceful shutdown**: Cleanup in `@app.on_event("shutdown")`
- **Logging**: Use Python's standard logging module
- **Testing**: Use `TestClient(app)` for integration tests

---

See related files:
- `/api/CLAUDE.md` — API structure
- `/services/CLAUDE.md` — Service layer
- `/models/CLAUDE.md` — Data schemas
- `/storage/CLAUDE.md` — Persistence
