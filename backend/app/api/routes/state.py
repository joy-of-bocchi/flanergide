"""State endpoint routes for short-term memory (mood, thoughts, blog)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthCredentials, HTTPBearer

from app.api.middleware.auth import verify_jwt
from app.config import settings
from app.models.schemas import (
    MoodUpdateRequest,
    MoodUpdateResponse,
    StateBloglResponse,
    StateCurrentResponse,
)
from app.services.state_manager import StateManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/state", tags=["state"])
security = HTTPBearer()


async def get_state_manager(request: Request) -> StateManager:
    """Get state manager from app state.

    Args:
        request: HTTP request

    Returns:
        StateManager instance
    """
    return request.app.state.state_manager


@router.get("/current", response_model=StateCurrentResponse)
async def get_current_state(
    request: Request,
    credentials: HTTPAuthCredentials = Depends(security),
    state_manager: StateManager = Depends(get_state_manager),
):
    """Get current mood, thoughts, and blog posts.

    Args:
        request: HTTP request
        credentials: JWT credentials
        state_manager: State manager service

    Returns:
        Current state with mood, thoughts, and blog posts

    Raises:
        HTTPException: If retrieval fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        # Get mood
        mood_data = await state_manager.get_current_mood()

        # Get thoughts and blog
        thoughts_data = await state_manager.get_recent_thoughts()

        logger.info(f"Retrieved current state for {device_id}")

        return StateCurrentResponse(
            mood=mood_data.get("mood", "neutral"),
            mood_updated_at=mood_data.get("updated_at", 0),
            thoughts=thoughts_data.get("thoughts", ""),
            thoughts_updated_at=thoughts_data.get("updated_at", 0),
            blog_posts=thoughts_data.get("blog_posts", [])
        )

    except Exception as e:
        logger.error(f"Failed to get current state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve state"
        )


@router.post("/update", response_model=MoodUpdateResponse)
async def update_mood(
    request: Request,
    update_req: MoodUpdateRequest,
    credentials: HTTPAuthCredentials = Depends(security),
    state_manager: StateManager = Depends(get_state_manager),
):
    """Update current mood from phone.

    Args:
        request: HTTP request
        update_req: Mood update request
        credentials: JWT credentials
        state_manager: State manager service

    Returns:
        Updated mood response

    Raises:
        HTTPException: If update fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        # Update mood
        mood_data = await state_manager.update_mood(
            mood=update_req.mood,
            context=update_req.context
        )

        logger.info(f"Updated mood to {update_req.mood} for {device_id}")

        return MoodUpdateResponse(
            mood=mood_data.get("mood"),
            updated_at=mood_data.get("updated_at"),
            acknowledgement=f"Mood updated to {mood_data.get('mood')}"
        )

    except ValueError as e:
        logger.warning(f"Invalid mood from {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to update mood: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update mood"
        )


@router.get("/blog", response_model=StateBloglResponse)
async def get_blog_posts(
    request: Request,
    credentials: HTTPAuthCredentials = Depends(security),
    state_manager: StateManager = Depends(get_state_manager),
):
    """Get cached blog post summaries.

    Args:
        request: HTTP request
        credentials: JWT credentials
        state_manager: State manager service

    Returns:
        Blog posts with cache metadata

    Raises:
        HTTPException: If retrieval fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        # Get thoughts (includes blog posts)
        thoughts_data = await state_manager.get_recent_thoughts()

        logger.info(f"Retrieved {len(thoughts_data.get('blog_posts', []))} blog posts for {device_id}")

        # Calculate next scrape time (currently static, could be dynamic)
        import time
        now = int(time.time())
        next_scrape = now + (settings.blog_scraper_interval_hours * 3600)

        return StateBloglResponse(
            blog_posts=thoughts_data.get("blog_posts", []),
            last_updated=thoughts_data.get("updated_at", 0),
            next_scrape=next_scrape
        )

    except Exception as e:
        logger.error(f"Failed to get blog posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve blog posts"
        )
