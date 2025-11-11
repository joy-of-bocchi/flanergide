# api/middleware/ — Authentication & Security

## Purpose

This directory contains middleware for securing API endpoints: JWT authentication, rate limiting, CORS, and request logging.

---

## Directory Structure

```
middleware/
├── CLAUDE.md       # This file
├── auth.py         # JWT token validation
└── security.py     # Rate limiting, CORS, security headers
```

---

## auth.py — JWT Authentication Middleware

Validates JWT tokens on all protected routes.

### JWT Token Format

**Token Structure** (from `/api/auth/token`):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJzdWIiOiJkZXZpY2UtMDAxIiwiZGV2aWNlX25hbWUiOiJQaXhlbCA3IiwiZXhwIjoxNjk5OTk5OTk5LCJpYXQiOjE2OTk4ODg4ODh9.
signature...
```

**Decoded Payload**:
```json
{
  "sub": "device-001",
  "device_name": "Pixel 7",
  "exp": 1699999999,
  "iat": 1699888888
}
```

**Fields**:
- `sub` — Device ID (unique identifier)
- `device_name` — User-friendly name
- `exp` — Expiration time (Unix timestamp)
- `iat` — Issued at time (Unix timestamp)

### Validation Process

1. **Extract token** from `Authorization: Bearer <token>` header
2. **Verify signature** using `JWT_SECRET` from config
3. **Check expiration** (not expired)
4. **Extract device_id** from `sub` claim
5. **Inject into request** context for logging/tracking

### Public Routes (Skip Auth)

Routes that **do not require JWT**:
- `GET /api/health` — Health check
- `GET /docs` — Swagger documentation
- `GET /redoc` — ReDoc documentation
- `POST /api/auth/token` — Initial token generation (admin only)

### Protected Routes (Require Auth)

All other routes require valid JWT:
- `POST /api/memory/store`
- `POST /api/memory/search`
- `GET /api/state/current`
- etc.

### Error Handling

**Missing Token**:
```json
{
  "detail": "Missing authorization header",
  "status_code": 401
}
```

**Invalid Signature**:
```json
{
  "detail": "Invalid token signature",
  "status_code": 401
}
```

**Expired Token**:
```json
{
  "detail": "Token has expired",
  "status_code": 401
}
```

**Malformed Token**:
```json
{
  "detail": "Malformed JWT token",
  "status_code": 401
}
```

### Implementation Pattern

```python
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import jwt
from app.config import settings

security = HTTPBearer()

async def verify_jwt(credentials: HTTPAuthCredentials) -> dict:
    """Verify JWT token and return claims"""
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        device_id = payload.get("sub")
        if not device_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token claims"
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid signature")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Decode error")

# In routes
@router.post("/memory/store")
async def store_event(
    event: EventSchema,
    credentials: HTTPAuthCredentials = Depends(security),
    vector_store: VectorStore = Depends(get_vector_store)
):
    claims = await verify_jwt(credentials)
    device_id = claims["sub"]
    # Store event with device_id metadata
    event_id = await vector_store.insert(event, device_id=device_id)
    return {"id": event_id, "stored": True}
```

### Token Refresh

For long-lived applications, support token refresh:

```python
@router.post("/api/auth/refresh")
async def refresh_token(
    credentials: HTTPAuthCredentials = Depends(security)
):
    """Generate new token from expired token"""
    try:
        # Decode without expiration check
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False}
        )
        # Generate new token
        new_token = jwt.encode(
            {
                "sub": payload["sub"],
                "device_name": payload.get("device_name"),
                "exp": datetime.utcnow() + timedelta(hours=24),
                "iat": datetime.utcnow()
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        return {
            "token": new_token,
            "expires_in": 86400
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Cannot refresh token")
```

---

## security.py — Rate Limiting, CORS, Security Headers

Protects against abuse and enforces security policies.

### Rate Limiting

**Purpose**: Prevent brute force and abuse

**Strategy**: Per-device rate limiting
- **Limit**: 100 requests/minute per device
- **Window**: Rolling minute
- **Response**: 429 Too Many Requests

**Implementation**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_device_id)

@router.post("/api/memory/store")
@limiter.limit("100/minute")
async def store_event(request: Request, ...):
    # Device ID from JWT is used as rate limit key
    pass
```

**Headers Returned**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1699888959
```

### CORS (Cross-Origin Resource Sharing)

**Purpose**: Only allow requests from your Android app

**Configuration**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app-domain.com",
        "https://flanergide.your-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Note**: Cloudflare Tunnel handles most CORS automatically (same origin). This is a secondary defense.

### Security Headers

**Headers Added**:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**Implementation**:
```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

### HTTPS Enforcement

**Cloudflare Tunnel handles HTTPS**:
- Certificate managed by Cloudflare
- Automatic renewal
- All traffic encrypted end-to-end

**Local Testing**:
- Use HTTP locally (localhost:8000)
- Tunnel handles encryption
- Production always HTTPS

---

## Middleware Registration Order

Order matters! Middleware runs bottom-to-top on request, top-to-bottom on response.

```python
# In app/main.py

# Outermost (runs first on request)
app.add_middleware(LoggingMiddleware)      # Log all requests
app.add_middleware(SecurityHeadersMiddleware)  # Add headers
app.add_middleware(CORSMiddleware)         # Handle CORS
app.add_middleware(RateLimitMiddleware)    # Rate limit
app.add_middleware(AuthMiddleware)         # Validate JWT
# Innermost (route handler)
```

**Request Flow** (left to right):
```
Request → Logging → SecurityHeaders → CORS → RateLimit → Auth → Handler
Response ← Logging ← SecurityHeaders ← CORS ← RateLimit ← Auth ← Handler
```

---

## Logging Pattern

Structured logging for security events:

```python
import logging

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Extract device ID from JWT (if available)
    device_id = "unknown"
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, ...)
            device_id = payload.get("sub")
        except:
            pass

    # Log request
    logger.info(
        f"{request.method} {request.url.path} | "
        f"device={device_id} | "
        f"ip={request.client.host}"
    )

    # Process request
    response = await call_next(request)

    # Log response
    logger.info(
        f"{request.method} {request.url.path} | "
        f"device={device_id} | "
        f"status={response.status_code} | "
        f"duration={response.headers.get('x-process-time')}ms"
    )

    return response
```

---

## Testing Middleware

### Test JWT Validation

```python
def test_missing_auth():
    response = client.post("/api/memory/store", json={...})
    assert response.status_code == 401

def test_invalid_token():
    headers = {"Authorization": "Bearer invalid-token"}
    response = client.post("/api/memory/store", headers=headers, json={...})
    assert response.status_code == 401

def test_valid_token():
    token = create_test_token(device_id="test-device")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/memory/store", headers=headers, json={...})
    assert response.status_code in [200, 201]
```

### Test Rate Limiting

```python
def test_rate_limit():
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Make 101 requests
    for i in range(100):
        response = client.post("/api/memory/store", headers=headers, json={...})
        assert response.status_code in [200, 201]

    # 101st request should be rate limited
    response = client.post("/api/memory/store", headers=headers, json={...})
    assert response.status_code == 429
```

---

## Notes for Implementation

- **Token Secret**: Generate with `secrets.token_hex(32)`, store in `.env`
- **Expiration**: 24 hours is reasonable, adjust based on usage patterns
- **Rate Limit Key**: Use device_id from JWT, not IP (device can move networks)
- **CORS Origins**: Use exact URLs, no wildcards
- **Security Headers**: Include all standard headers
- **Logging**: Don't log sensitive data (tokens, passwords)

---

See related files:
- `../CLAUDE.md` — API layer overview
- `../routes/CLAUDE.md` — Endpoint definitions
- `../../app/CLAUDE.md` — Application setup
- `../../config.py` — JWT secret and settings
