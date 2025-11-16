"""Captured text logs endpoint for device text capture uploads."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.api.middleware.auth import verify_jwt
from app.config import settings
from app.models.schemas import (
    CapturedTextLogsSearchRequest,
    CapturedTextLogsSearchResponse,
    CapturedTextLogsSearchResult,
    CapturedTextLogsUploadRequest,
    CapturedTextLogsUploadResponse,
)
from app.services.log_accumulator import LogAccumulator
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/logs", tags=["logs"])
security = HTTPBearer()


async def get_vector_store(request: Request) -> VectorStore:
    """Get vector store from app state.

    Args:
        request: HTTP request

    Returns:
        VectorStore instance
    """
    return request.app.state.vector_store


async def get_log_accumulator(request: Request) -> LogAccumulator:
    """Get log accumulator from app state.

    Args:
        request: HTTP request

    Returns:
        LogAccumulator instance
    """
    return request.app.state.log_accumulator


@router.post("/upload", response_model=CapturedTextLogsUploadResponse, status_code=201)
async def upload_logs(
    request: Request,
    upload_req: CapturedTextLogsUploadRequest,
    credentials = Depends(security),
    vector_store: VectorStore = Depends(get_vector_store),
    log_accumulator: LogAccumulator = Depends(get_log_accumulator),
) -> CapturedTextLogsUploadResponse:
    """Upload batch of captured text logs from device.

    Accepts a batch of redacted text logs and stores them in the vector database
    for semantic search and analysis.

    Args:
        request: HTTP request
        upload_req: Batch of logs to upload
        credentials: JWT credentials
        vector_store: Vector store service

    Returns:
        Upload response with success count and status

    Raises:
        HTTPException: If authentication fails or upload fails
    """
    # Log incoming request
    logger.info(f"=== Received log upload request ===")
    logger.info(f"Number of logs: {len(upload_req.logs)}")
    logger.info(f"Client IP: {request.client.host if request.client else 'unknown'}")

    # Verify JWT
    try:
        payload = await verify_jwt(
            credentials, settings.jwt_secret, settings.jwt_algorithm
        )
        device_id = payload.get("sub", "unknown")
        logger.info(f"Authenticated device: {device_id}")
    except HTTPException as e:
        logger.warning(f"JWT verification failed: {e.detail}")
        raise

    uploaded_count = 0
    failed_count = 0
    failed_indices = []

    # Process each log entry
    for idx, log_entry in enumerate(upload_req.logs):
        try:
            # Log the received entry
            logger.info(
                f"Log entry {idx+1}/{len(upload_req.logs)}: "
                f"app={log_entry.appPackage}, "
                f"text='{log_entry.text[:100]}...', "
                f"timestamp={log_entry.timestamp}"
            )

            # Create event for vector store
            event_data = {
                "type": "captured_text",
                "text": log_entry.text,
                "appPackage": log_entry.appPackage,
                "deviceId": log_entry.deviceId or device_id,
                "timestamp": log_entry.timestamp,
            }

            # Generate unique ID for this log entry
            event_id = await vector_store.insert(event_data, device_id=device_id)

            if event_id:
                uploaded_count += 1
                logger.info(
                    f"Successfully stored log {event_id}: {log_entry.appPackage}"
                )

                # Also accumulate to daily log file for summarization analysis
                try:
                    log_accumulator.append_text_log(
                        text=log_entry.text,
                        app_package=log_entry.appPackage,
                        timestamp=log_entry.timestamp,
                        device_id=log_entry.deviceId or device_id
                    )
                except Exception as e:
                    # Log but don't fail the upload if accumulation fails
                    logger.warning(f"Failed to accumulate log to file: {e}")
            else:
                failed_count += 1
                failed_indices.append(idx)
                logger.warning(f"Failed to store log entry {idx}")

        except Exception as e:
            logger.error(f"Failed to store log entry {idx}: {e}")
            failed_count += 1
            failed_indices.append(idx)

    # Determine overall status
    if failed_count == 0:
        status_str = "success"
        message = f"{uploaded_count} logs stored successfully"
    elif uploaded_count == 0:
        status_str = "failed"
        message = f"Failed to store all {failed_count} logs"
    else:
        status_str = "partial"
        message = f"Stored {uploaded_count}, failed {failed_count}"

    logger.info(
        f"Log upload from {device_id}: {uploaded_count} uploaded, "
        f"{failed_count} failed out of {len(upload_req.logs)} total"
    )

    return CapturedTextLogsUploadResponse(
        uploaded=uploaded_count,
        failed=failed_count,
        status=status_str,
        message=message,
    )


@router.post("/search", response_model=CapturedTextLogsSearchResponse)
async def search_logs(
    request: Request,
    search_req: CapturedTextLogsSearchRequest,
    credentials = Depends(security),
    vector_store: VectorStore = Depends(get_vector_store),
) -> CapturedTextLogsSearchResponse:
    """Semantic search over captured text logs.

    Searches the vector database for text logs matching the query using
    semantic similarity. Supports filtering by app package and timestamp range.

    Args:
        request: HTTP request
        search_req: Search request with query and filters
        credentials: JWT credentials
        vector_store: Vector store service

    Returns:
        Search results with matching logs and similarity scores

    Raises:
        HTTPException: If authentication fails or search fails
    """
    # Verify JWT
    try:
        payload = await verify_jwt(
            credentials, settings.jwt_secret, settings.jwt_algorithm
        )
        device_id = payload.get("sub", "unknown")
    except HTTPException as e:
        logger.warning(f"JWT verification failed: {e.detail}")
        raise

    try:
        # Build filters
        filters = {}
        if search_req.appPackage:
            filters["appPackage"] = search_req.appPackage
        if search_req.timestamp_min is not None:
            filters["timestamp_min"] = search_req.timestamp_min
        if search_req.timestamp_max is not None:
            filters["timestamp_max"] = search_req.timestamp_max

        # Perform semantic search
        results = await vector_store.search(
            query=search_req.query,
            limit=search_req.limit,
            filters=filters if filters else None,
        )

        # Transform results to match expected schema
        search_results = []
        for result in results:
            data = result.get("data", {})
            search_results.append(
                CapturedTextLogsSearchResult(
                    id=result.get("id", str(uuid.uuid4())),
                    text=data.get("text", ""),
                    appPackage=data.get("appPackage", "unknown"),
                    timestamp=data.get("timestamp", 0),
                    deviceId=data.get("deviceId", "unknown"),
                    similarity_score=result.get("similarity_score"),
                )
            )

        logger.info(
            f"Text log search from {device_id}: '{search_req.query}' "
            f"returned {len(search_results)} results"
        )

        return CapturedTextLogsSearchResponse(
            results=search_results,
            count=len(search_results),
            total=len(search_results),
        )

    except Exception as e:
        logger.error(f"Text log search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        )
