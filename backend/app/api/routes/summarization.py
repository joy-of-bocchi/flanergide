"""Summarization generation API endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.api.middleware.auth import verify_jwt
from app.config import get_settings
from app.models.summarization import SummaryResponse, SummaryMetadata
from app.services.summarization_service import SummarizationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/summary", tags=["summary"])
security = HTTPBearer()
settings = get_settings()


async def get_summary_service(request: Request) -> SummarizationService:
    """Dependency injection for summary service."""
    return request.app.state.summarization_service


@router.get(
    "/yesterday",
    response_model=SummaryResponse,
    summary="Generate summary for yesterday"
)
async def get_yesterday_summary(
    request: Request,
    credentials=Depends(security),
    summary_service: SummarizationService = Depends(get_summary_service)
):
    """Generate daily summary for yesterday.

    Analyzes:
    - Phone text logs from yesterday
    - Blog posts published yesterday
    - Provides insights on activities, thoughts, mood, and personality

    Returns:
        Markdown summary with analysis sections
    """
    try:
        # Verify JWT
        payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
        device_id = payload.get("sub", "unknown")
        logger.info(f"Generating yesterday summary for device {device_id}")

        # Calculate yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Generate summary
        result = await summary_service.generate_daily_summary(date=yesterday)

        return SummaryResponse(
            summary=result["summary"],
            metadata=SummaryMetadata(**result["metadata"]),
            log_file_path=result["log_file_path"],
            summary_file_path=result["summary_file_path"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate yesterday summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {str(e)}"
        )


@router.get(
    "/today",
    response_model=SummaryResponse,
    summary="Generate summary for today"
)
async def get_today_summary(
    request: Request,
    credentials=Depends(security),
    summary_service: SummarizationService = Depends(get_summary_service)
):
    """Generate summary for today (in-progress day).

    Analyzes:
    - Phone text logs from today so far
    - Blog posts published today
    - Provides insights on activities, thoughts, mood, and personality

    Note: This is an in-progress analysis. Data may be incomplete.

    Returns:
        Markdown summary with analysis sections
    """
    try:
        # Verify JWT
        payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
        device_id = payload.get("sub", "unknown")
        logger.info(f"Generating today summary for device {device_id}")

        # Generate summary for today
        result = await summary_service.generate_today_summary()

        return SummaryResponse(
            summary=result["summary"],
            metadata=SummaryMetadata(**result["metadata"]),
            log_file_path=result["log_file_path"],
            summary_file_path=result["summary_file_path"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate today summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {str(e)}"
        )


@router.get(
    "/week",
    response_model=SummaryResponse,
    summary="Generate weekly summary"
)
async def get_weekly_summary(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    credentials=Depends(security),
    summary_service: SummarizationService = Depends(get_summary_service)
):
    """Generate weekly summary for a date range.

    Query Parameters:
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 7 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)

    Analyzes:
    - Phone text logs from the week
    - Blog posts published during the week
    - Provides insights on patterns, themes, mood trends, and personality

    Returns:
        Markdown summary with analysis sections
    """
    try:
        # Verify JWT
        payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
        device_id = payload.get("sub", "unknown")

        # Validate date formats if provided
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_date must be in YYYY-MM-DD format"
                )

        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="end_date must be in YYYY-MM-DD format"
                )

        logger.info(f"Generating weekly summary for device {device_id} ({start_date} to {end_date})")

        # Generate summary
        result = await summary_service.generate_weekly_summary(
            start_date=start_date,
            end_date=end_date
        )

        return SummaryResponse(
            summary=result["summary"],
            metadata=SummaryMetadata(**result["metadata"]),
            log_file_path=result["log_file_path"],
            summary_file_path=result["summary_file_path"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate weekly summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {str(e)}"
        )


@router.get(
    "/date/{date}",
    response_model=SummaryResponse,
    summary="Generate summary for specific date"
)
async def get_date_summary(
    request: Request,
    date: str,
    credentials=Depends(security),
    summary_service: SummarizationService = Depends(get_summary_service)
):
    """Generate daily summary for a specific date.

    Path Parameters:
        date: Date in YYYY-MM-DD format

    Analyzes:
    - Phone text logs from the specified date
    - Blog posts published on that date
    - Provides insights on activities, thoughts, mood, and personality

    Returns:
        Markdown summary with analysis sections
    """
    try:
        # Verify JWT
        payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
        device_id = payload.get("sub", "unknown")

        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date must be in YYYY-MM-DD format"
            )

        logger.info(f"Generating summary for {date} for device {device_id}")

        # Generate summary
        result = await summary_service.generate_daily_summary(date=date)

        return SummaryResponse(
            summary=result["summary"],
            metadata=SummaryMetadata(**result["metadata"]),
            log_file_path=result["log_file_path"],
            summary_file_path=result["summary_file_path"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate summary for {date}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {str(e)}"
        )
