"""Commentary generation API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.api.middleware.auth import verify_jwt
from app.config import get_settings
from app.models.commentary import CommentaryRequest, CommentaryResponse
from app.prompts.commentary_prompts import get_next_prompt
from app.services.commentary_service import CommentaryService, DEFAULT_DAYS_OF_DATA, DEFAULT_WEEKS_OF_BLOGS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/commentary", tags=["commentary"])
security = HTTPBearer()
settings = get_settings()


async def get_commentary_service(request: Request) -> CommentaryService:
    """Dependency injection for commentary service."""
    return request.app.state.commentary_service


@router.post(
    "/generate",
    response_model=CommentaryResponse,
    summary="Generate life commentary"
)
async def generate_commentary(
    request: Request,
    commentary_request: CommentaryRequest,
    credentials=Depends(security),
    commentary_service: CommentaryService = Depends(get_commentary_service)
):
    """Generate AI commentary on life patterns and activities.

    Request Body:
        days_of_data: Number of past days of log data to analyze (1-30)
        weeks_of_blogs: Number of weeks of blog posts to include (1-12)
        prompt: Commentary prompt template to use for generation

    Analyzes:
    - Phone text logs from recent days
    - Blog posts from recent weeks
    - Generates commentary using the provided prompt perspective

    Returns:
        Generated commentary text with metadata
    """
    try:
        # Verify JWT
        payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
        device_id = payload.get("sub", "unknown")
        logger.info(
            f"Generating commentary for device {device_id} "
            f"({commentary_request.days_of_data} days, {commentary_request.weeks_of_blogs} weeks)"
        )

        # Generate commentary (prompt_index will be provided by caller)
        result = await commentary_service.generate_commentary(
            days_of_data=commentary_request.days_of_data,
            weeks_of_blogs=commentary_request.weeks_of_blogs,
            prompt=commentary_request.prompt,
            prompt_index=0  # When called manually, index is not tracked
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate commentary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Commentary generation failed: {str(e)}"
        )


@router.get(
    "/generate-auto",
    response_model=CommentaryResponse,
    summary="Auto-generate commentary with round-robin prompts"
)
async def generate_auto_commentary(
    request: Request,
    credentials=Depends(security),
    commentary_service: CommentaryService = Depends(get_commentary_service)
):
    """Automatically generate commentary using round-robin prompt rotation.

    This endpoint is used by the background task for automatic commentary generation.
    It uses default settings (3 days of data, 2 weeks of blogs) and rotates through
    10 different prompt perspectives.

    Returns:
        Generated commentary text with metadata including which prompt was used
    """
    try:
        # Verify JWT
        payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
        device_id = payload.get("sub", "unknown")

        # Get next prompt in rotation
        prompt_template, prompt_index = get_next_prompt()

        logger.info(
            f"Auto-generating commentary for device {device_id} "
            f"with prompt {prompt_index} (defaults: {DEFAULT_DAYS_OF_DATA} days, {DEFAULT_WEEKS_OF_BLOGS} weeks)"
        )

        # Generate commentary with defaults
        result = await commentary_service.generate_commentary(
            days_of_data=DEFAULT_DAYS_OF_DATA,
            weeks_of_blogs=DEFAULT_WEEKS_OF_BLOGS,
            prompt=prompt_template,
            prompt_index=prompt_index
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to auto-generate commentary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto commentary generation failed: {str(e)}"
        )
