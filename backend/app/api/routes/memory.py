"""Memory endpoint routes for long-term memory (Chroma)."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from app.api.middleware.auth import extract_device_id, verify_jwt
from app.config import settings
from app.models.schemas import (
    MemoryRecentResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryStoreRequest,
    MemoryStoreResponse,
)
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])
security = HTTPBearer()


async def get_vector_store(request: Request) -> VectorStore:
    """Get vector store from app state.

    Args:
        request: HTTP request

    Returns:
        VectorStore instance
    """
    return request.app.state.vector_store


async def get_device_id(
    credentials = Depends(security),
) -> str:
    """Extract and verify device ID from JWT.

    Args:
        credentials: HTTP credentials with JWT token

    Returns:
        Device ID

    Raises:
        HTTPException: If token is invalid
    """
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    return payload.get("sub", "unknown")


@router.post("/store", response_model=MemoryStoreResponse, status_code=201)
async def store_event(
    request: Request,
    event: MemoryStoreRequest,
    credentials = Depends(security),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Store a new event with embedding.

    Args:
        request: HTTP request
        event: Event to store
        credentials: JWT credentials
        vector_store: Vector store service

    Returns:
        Event storage response with ID

    Raises:
        HTTPException: If storage fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        # Store event
        event_id = await vector_store.insert(event.model_dump(), device_id=device_id)

        logger.info(f"Stored event {event_id} from device {device_id}")

        return MemoryStoreResponse(
            id=event_id,
            stored=True,
            embedding_dim=384  # Default embedding dimension
        )

    except ValueError as e:
        logger.warning(f"Invalid event from {device_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to store event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store event"
        )


@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(
    request: Request,
    search_req: MemorySearchRequest,
    credentials = Depends(security),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Semantic search over stored events.

    Args:
        request: HTTP request
        search_req: Search request
        credentials: JWT credentials
        vector_store: Vector store service

    Returns:
        Search results with similarity scores

    Raises:
        HTTPException: If search fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        # Perform search
        results = await vector_store.search(
            query=search_req.query,
            limit=search_req.limit,
            filters=search_req.filters.model_dump() if search_req.filters else None
        )

        logger.info(f"Search from {device_id}: '{search_req.query}' returned {len(results)} results")

        return MemorySearchResponse(
            results=results,
            count=len(results),
            total=len(results)  # Simplified: return count as total
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get("/recent", response_model=MemoryRecentResponse)
async def get_recent(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    type_filter: Optional[str] = None,
    credentials = Depends(security),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Get recent events without semantic search.

    Args:
        request: HTTP request
        limit: Number of results
        offset: Skip first N results
        type_filter: Optional event type filter
        credentials: JWT credentials
        vector_store: Vector store service

    Returns:
        Recent events with pagination

    Raises:
        HTTPException: If retrieval fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        # Validate limit
        if limit < 1 or limit > 100:
            limit = 20
        if offset < 0:
            offset = 0

        # Get recent events
        results, total = await vector_store.recent(
            limit=limit,
            offset=offset,
            type_filter=type_filter
        )

        logger.info(f"Retrieved {len(results)} recent events for {device_id}")

        return MemoryRecentResponse(
            results=results,
            count=len(results),
            total=total,
            has_more=(offset + limit) < total
        )

    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve events"
        )


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    request: Request,
    event_id: str,
    credentials = Depends(security),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Delete an event from memory.

    Args:
        request: HTTP request
        event_id: Event ID to delete
        credentials: JWT credentials
        vector_store: Vector store service

    Raises:
        HTTPException: If event not found or deletion fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        success = await vector_store.delete(event_id)

        if not success:
            logger.warning(f"Event {event_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        logger.info(f"Deleted event {event_id} from device {device_id}")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete event"
        )
