"""FastAPI application entry point."""

import asyncio
import logging
import logging.config
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.middleware.security import (
    add_security_headers,
    init_rate_limiter,
    logging_middleware,
    rate_limit_check_middleware,
    setup_cors,
)
from app.api.routes import summarization, logs, memory, state, sync
from app.config import settings
from app.services.blog_scraper import BlogScraper
from app.services.summarization_service import SummarizationService
from app.services.log_accumulator import LogAccumulator
from app.services.state_manager import StateManager
from app.services.summarizer import Summarizer
from app.services.vector_store import VectorStore

# Configure logging
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "access": {
            "format": "%(asctime)s | ACCESS | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        }
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": settings.log_level,
            "propagate": True
        },
        "uvicorn.access": {
            "handlers": ["access"],
            "level": "INFO",
            "propagate": False
        }
    }
}

logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)


# Create FastAPI app
app = FastAPI(
    title="Flanergide Backend",
    description="Secure home server backend for personal AI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Setup security middleware
setup_cors(
    app,
    allowed_origins=[
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        settings.cloudflare_tunnel_url
    ]
)

# Add middleware stack (order matters - last added runs first)
from starlette.middleware.base import BaseHTTPMiddleware
app.middleware("http")(logging_middleware)
app.middleware("http")(add_security_headers)
if settings.enable_rate_limiting:
    app.middleware("http")(rate_limit_check_middleware)

# Initialize rate limiter
if settings.enable_rate_limiting:
    init_rate_limiter(settings.rate_limit_requests_per_minute)


# Background task for blog scraper
async def run_blog_scraper_task():
    """Background task to run blog scraper periodically."""
    logger.info("Blog scraper background task started")

    while True:
        try:
            if settings.enable_blog_scraper:
                logger.info("=" * 80)
                logger.info("Blog scraper: Starting scheduled run")
                logger.info("=" * 80)

                # Fetch posts from blog
                posts = await app.state.blog_scraper.fetch_and_parse()

                if posts:
                    logger.info(f"Blog scraper: Fetched {len(posts)} posts, checking for new content...")

                    # Get existing cached posts to check for duplicates
                    existing_posts = await app.state.state_manager.get_recent_thoughts()
                    existing_urls = {post.get("url") for post in existing_posts.get("blog_posts", [])}

                    # Filter only new posts (by URL)
                    new_posts = [post for post in posts if post.get("url") not in existing_urls]

                    if new_posts:
                        logger.info(f"Blog scraper: Found {len(new_posts)} new posts, updating cache...")

                        # Update cache with all posts (new + existing will be merged by state manager)
                        success = await app.state.state_manager.update_blog_cache(
                            posts,
                            summarizer=app.state.summarizer
                        )

                        if success:
                            logger.info(f"✓ Blog scraper: Successfully processed {len(new_posts)} new posts")
                        else:
                            logger.warning("✗ Blog scraper: Cache update failed")
                    else:
                        logger.info("Blog scraper: No new posts found, skipping update")
                else:
                    logger.warning("Blog scraper: No posts fetched from blog")

                logger.info("=" * 80)
            else:
                logger.debug("Blog scraper disabled in config, skipping run")

        except Exception as e:
            logger.error(f"Blog scraper task error: {e}", exc_info=True)

        # Wait for next run (interval in hours from settings)
        interval_seconds = settings.blog_scraper_interval_hours * 3600
        logger.info(f"Blog scraper: Next run in {settings.blog_scraper_interval_hours} hours")
        await asyncio.sleep(interval_seconds)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize on app startup."""
    logger.info("=" * 80)
    logger.info("Starting Flanergide Backend")
    logger.info("=" * 80)

    try:
        # Create storage directories
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        os.makedirs(settings.state_dir, exist_ok=True)
        os.makedirs(settings.analysis_dir, exist_ok=True)
        logger.info(f"Storage directories ready: {settings.chroma_persist_dir}")

        # Initialize services
        logger.info("Initializing services...")

        # Vector store (Chroma)
        vector_store = VectorStore(settings.chroma_persist_dir)
        app.state.vector_store = vector_store
        logger.info(f"Vector store initialized with {vector_store.count()} events")

        # State manager
        state_manager = StateManager(settings.state_dir)
        app.state.state_manager = state_manager
        logger.info("State manager initialized")

        # Blog scraper
        blog_scraper = BlogScraper(settings.blog_url)
        app.state.blog_scraper = blog_scraper
        logger.info(f"Blog scraper configured for {settings.blog_url}")

        # Summarizer (Ollama)
        summarizer = Summarizer(settings.ollama_host)
        app.state.summarizer = summarizer
        logger.info(f"Summarizer initialized with Ollama at {settings.ollama_host}")

        # Log accumulator (for summarization system)
        log_accumulator = LogAccumulator(settings.analysis_dir)
        app.state.log_accumulator = log_accumulator
        logger.info(f"Log accumulator initialized at {settings.analysis_dir}")

        # Summarization service
        summarization_service = SummarizationService(
            log_accumulator=log_accumulator,
            state_manager=state_manager,
            summarizer=summarizer,
            analysis_dir=settings.analysis_dir
        )
        app.state.summarization_service = summarization_service
        logger.info("Summarization service initialized")

        logger.info("All services initialized successfully")
        logger.info("=" * 80)

        # Start background blog scraper task
        if settings.enable_blog_scraper:
            asyncio.create_task(run_blog_scraper_task())
            logger.info(f"Blog scraper background task scheduled (interval: {settings.blog_scraper_interval_hours}h)")
        else:
            logger.info("Blog scraper disabled in config")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown."""
    logger.info("Shutting down Flanergide Backend...")
    # Cleanup code here if needed


# Health check endpoint (no auth required)
@app.get("/api/health")
async def health_check():
    """Health check endpoint.

    Returns:
        Health status
    """
    return {"status": "ok", "service": "Flanergide Backend"}


# Include routers
app.include_router(logs.router)
app.include_router(memory.router)
app.include_router(state.router)
app.include_router(sync.router)
app.include_router(summarization.router)


# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions.

    Args:
        request: HTTP request
        exc: Exception

    Returns:
        JSON error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error"
            },
            "timestamp": int(__import__("time").time())
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint.

    Returns:
        API information
    """
    return {
        "name": "Flanergide Backend",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
