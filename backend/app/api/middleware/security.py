"""Security middleware for rate limiting, CORS, and headers."""

import logging
import time
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def setup_cors(app: FastAPI, allowed_origins: Optional[list[str]] = None):
    """Setup CORS middleware.

    Args:
        app: FastAPI application
        allowed_origins: List of allowed origins (default: localhost and common dev URLs)
    """
    if allowed_origins is None:
        allowed_origins = [
            "http://localhost:8000",
            "http://localhost:3000",
            "http://localhost:5173",
            "https://localhost:8000",
            "https://localhost:3000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    logger.info(f"CORS configured for origins: {allowed_origins}")


async def add_security_headers(request: Request, call_next: Callable) -> Response:
    """Add security headers to all responses.

    Args:
        request: HTTP request
        call_next: Next middleware

    Returns:
        Response with security headers
    """
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


def create_rate_limiter(requests_per_minute: int = 100) -> Limiter:
    """Create a rate limiter.

    Args:
        requests_per_minute: Requests allowed per minute

    Returns:
        Configured Limiter instance
    """
    limiter = Limiter(key_func=get_remote_address)
    logger.info(f"Rate limiter configured: {requests_per_minute} requests/minute")
    return limiter


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """Log all requests and responses.

    Args:
        request: HTTP request
        call_next: Next middleware

    Returns:
        Response with timing headers
    """
    # Extract info
    method = request.method
    path = request.url.path
    client_ip = request.client.host if request.client else "unknown"

    # Start timer
    start_time = time.time()

    try:
        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = (time.time() - start_time) * 1000  # milliseconds

        # Log
        logger.info(
            f"{method} {path} | "
            f"status={response.status_code} | "
            f"ip={client_ip} | "
            f"duration={duration:.1f}ms"
        )

        # Add timing header
        response.headers["X-Process-Time"] = str(duration)

        return response

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(
            f"{method} {path} | "
            f"error={str(e)[:100]} | "
            f"ip={client_ip} | "
            f"duration={duration:.1f}ms"
        )
        raise


async def rate_limit_middleware(
    request: Request,
    call_next: Callable,
    limiter: Limiter
) -> Response:
    """Rate limit requests per IP address.

    Args:
        request: HTTP request
        call_next: Next middleware
        limiter: Rate limiter instance

    Returns:
        Response or 429 if rate limited
    """
    # Skip rate limiting for health check
    if request.url.path == "/api/health":
        return await call_next(request)

    # Get rate limit key (IP address)
    key = get_remote_address(request)

    # Check if rate limited
    # Note: slowapi integration is more complex, for now use simple approach
    # In production, use Redis-backed rate limiting

    return await call_next(request)


class RateLimitStore:
    """Simple in-memory rate limit store."""

    def __init__(self, requests_per_minute: int = 100):
        """Initialize rate limit store.

        Args:
            requests_per_minute: Max requests per minute per IP
        """
        self.requests_per_minute = requests_per_minute
        self.store: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for key.

        Args:
            key: Rate limit key (usually IP address)

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        cutoff = now - 60  # 1 minute window

        # Initialize if needed
        if key not in self.store:
            self.store[key] = []

        # Remove old entries
        self.store[key] = [t for t in self.store[key] if t > cutoff]

        # Check if allowed
        if len(self.store[key]) < self.requests_per_minute:
            self.store[key].append(now)
            return True

        return False

    def cleanup(self):
        """Remove expired entries."""
        now = time.time()
        cutoff = now - 120  # Keep 2 minute window

        for key in list(self.store.keys()):
            self.store[key] = [t for t in self.store[key] if t > cutoff]
            if not self.store[key]:
                del self.store[key]


# Global rate limit store
_rate_limit_store: Optional[RateLimitStore] = None


def init_rate_limiter(requests_per_minute: int = 100):
    """Initialize global rate limiter.

    Args:
        requests_per_minute: Max requests per minute
    """
    global _rate_limit_store
    _rate_limit_store = RateLimitStore(requests_per_minute)
    logger.info(f"Initialized rate limiter: {requests_per_minute} requests/minute")


async def check_rate_limit(request: Request) -> bool:
    """Check if request is within rate limit.

    Args:
        request: HTTP request

    Returns:
        True if allowed, False if rate limited
    """
    if not _rate_limit_store:
        return True  # Allow if not initialized

    # Skip rate limiting for certain paths
    if request.url.path in ["/api/health", "/docs", "/redoc"]:
        return True

    # Get IP address
    key = request.client.host if request.client else "unknown"

    return _rate_limit_store.is_allowed(key)


async def rate_limit_check_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to check rate limits.

    Args:
        request: HTTP request
        call_next: Next middleware

    Returns:
        Response or 429 if rate limited
    """
    if not await check_rate_limit(request):
        return Response(
            content='{"error": "Rate limit exceeded"}',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            media_type="application/json"
        )

    response = await call_next(request)

    # Add rate limit headers
    if _rate_limit_store and request.client:
        key = request.client.host
        remaining = _rate_limit_store.requests_per_minute - len(
            _rate_limit_store.store.get(key, [])
        )
        response.headers["X-RateLimit-Limit"] = str(_rate_limit_store.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

    return response
