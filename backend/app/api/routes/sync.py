"""Sync endpoint routes for device synchronization."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthCredentials, HTTPBearer

from app.api.middleware.auth import verify_jwt
from app.config import settings
from app.models.schemas import (
    SyncContext,
    SyncPullRequest,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncPushResult,
)
from app.services.state_manager import StateManager
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sync", tags=["sync"])
security = HTTPBearer()


async def get_vector_store(request: Request) -> VectorStore:
    """Get vector store from app state.

    Args:
        request: HTTP request

    Returns:
        VectorStore instance
    """
    return request.app.state.vector_store


async def get_state_manager(request: Request) -> StateManager:
    """Get state manager from app state.

    Args:
        request: HTTP request

    Returns:
        StateManager instance
    """
    return request.app.state.state_manager


@router.post("/pull", response_model=SyncPullResponse)
async def sync_pull(
    request: Request,
    pull_req: SyncPullRequest,
    credentials: HTTPAuthCredentials = Depends(security),
    vector_store: VectorStore = Depends(get_vector_store),
    state_manager: StateManager = Depends(get_state_manager),
):
    """Pull complete state sync (memory + current state + context).

    Args:
        request: HTTP request
        pull_req: Pull request with last sync timestamp
        credentials: JWT credentials
        vector_store: Vector store service
        state_manager: State manager service

    Returns:
        Complete sync response with state and recent memories

    Raises:
        HTTPException: If sync fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        # Get current state
        current_state = await state_manager.get_current_state()

        # Get recent events since last sync
        recent_memories, total = await vector_store.recent(
            limit=50,
            offset=0,
            type_filter=None
        )

        # Filter by timestamp if provided
        if pull_req.last_sync_timestamp > 0:
            recent_memories = [
                m for m in recent_memories
                if m.get("timestamp", 0) > pull_req.last_sync_timestamp
            ]

        # Get current timestamp
        now = int(time.time())

        logger.info(
            f"Sync pull from {device_id}: "
            f"{len(recent_memories)} new memories, "
            f"mood={current_state['mood']}"
        )

        return SyncPullResponse(
            current_state={
                "mood": current_state["mood"],
                "mood_context": current_state["mood_context"],
                "thoughts": current_state["thoughts"],
                "blog_posts": current_state["blog_posts"]
            },
            recent_memories=recent_memories,
            context=SyncContext(
                last_sync=pull_req.last_sync_timestamp,
                new_events_count=len(recent_memories),
                server_time=now
            )
        )

    except Exception as e:
        logger.error(f"Sync pull failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sync failed"
        )


@router.post("/push", response_model=SyncPushResponse, status_code=201)
async def sync_push(
    request: Request,
    push_req: SyncPushRequest,
    credentials: HTTPAuthCredentials = Depends(security),
    vector_store: VectorStore = Depends(get_vector_store),
):
    """Push batch of events from phone to server.

    Args:
        request: HTTP request
        push_req: Push request with events
        credentials: JWT credentials
        vector_store: Vector store service

    Returns:
        Push response with success/failure for each event

    Raises:
        HTTPException: If push fails
    """
    # Verify JWT
    payload = await verify_jwt(credentials, settings.jwt_secret, settings.jwt_algorithm)
    device_id = payload.get("sub", "unknown")

    try:
        results = []
        stored_count = 0
        failed_count = 0

        for i, event in enumerate(push_req.events):
            try:
                # Store event
                event_id = await vector_store.insert(event, device_id=device_id)
                results.append(
                    SyncPushResult(
                        event_index=i,
                        id=event_id,
                        success=True,
                        error=None
                    )
                )
                stored_count += 1

            except Exception as e:
                logger.warning(f"Failed to store event {i}: {e}")
                results.append(
                    SyncPushResult(
                        event_index=i,
                        id=None,
                        success=False,
                        error=str(e)[:100]
                    )
                )
                failed_count += 1

        logger.info(
            f"Sync push from {device_id}: "
            f"stored={stored_count}, failed={failed_count}"
        )

        return SyncPushResponse(
            stored_count=stored_count,
            failed_count=failed_count,
            results=results
        )

    except Exception as e:
        logger.error(f"Sync push failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Push failed"
        )
