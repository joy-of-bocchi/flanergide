"""State endpoint routes for short-term memory (mood, thoughts, blog)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.api.middleware.auth import verify_jwt
from app.config import settings
from app.models.schemas import (
    MoodUpdateRequest,
    MoodUpdateResponse,
    StateBlogResponse,
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
    credentials = Depends(security),
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
    credentials = Depends(security),
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


@router.get("/blog", response_model=StateBlogResponse)
async def get_blog_posts(
    request: Request,
    credentials = Depends(security),
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

        return StateBlogResponse(
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


@router.post("/blog/scrape")
async def trigger_blog_scrape(
    request: Request,
    credentials = Depends(security),
    state_manager: StateManager = Depends(get_state_manager),
):
    """Manually trigger blog scraper (for testing/debugging).

    Args:
        request: HTTP request
        credentials: JWT credentials
        state_manager: State manager service

    Returns:
        Scrape results

    Raises:
        HTTPException: If scrape fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        logger.info(f"Manual blog scrape triggered by {device_id}")

        if not settings.enable_blog_scraper:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Blog scraper is disabled in configuration"
            )

        # Get services from app state
        blog_scraper = request.app.state.blog_scraper
        summarizer = request.app.state.summarizer

        # Fetch posts from blog
        posts = await blog_scraper.fetch_and_parse()

        if not posts:
            logger.warning("Manual scrape: No posts fetched from blog")
            return {
                "success": True,
                "posts_fetched": 0,
                "posts_new": 0,
                "posts_total": 0,
                "message": "No posts found at blog URL"
            }

        logger.info(f"Manual scrape: Fetched {len(posts)} posts from blog")

        # Get existing cached posts
        existing_posts = await state_manager.get_recent_thoughts()
        existing_urls = {post.get("url") for post in existing_posts.get("blog_posts", [])}

        # Filter only new posts
        new_posts = [post for post in posts if post.get("url") not in existing_urls]

        if new_posts:
            logger.info(f"Manual scrape: Found {len(new_posts)} new posts, updating cache...")

            # Update cache
            success = await state_manager.update_blog_cache(posts, summarizer=summarizer)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update blog cache"
                )

            # Get updated total count
            updated_posts = await state_manager.get_recent_thoughts()
            total_count = len(updated_posts.get("blog_posts", []))

            logger.info(f"Manual scrape: Successfully processed {len(new_posts)} new posts")

            return {
                "success": True,
                "posts_fetched": len(posts),
                "posts_new": len(new_posts),
                "posts_total": total_count,
                "message": f"Scraped and cached {len(new_posts)} new posts"
            }
        else:
            logger.info("Manual scrape: No new posts found")
            return {
                "success": True,
                "posts_fetched": len(posts),
                "posts_new": 0,
                "posts_total": len(existing_posts.get("blog_posts", [])),
                "message": "No new posts found"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual blog scrape failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Blog scrape failed: {str(e)}"
        )
