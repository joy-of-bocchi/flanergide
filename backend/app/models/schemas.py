"""Pydantic models for API requests and responses."""

from typing import Optional
from pydantic import BaseModel, Field


# ============================================================================
# Health & Basic
# ============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Status")


# ============================================================================
# Memory Store
# ============================================================================


class MemoryStoreRequest(BaseModel):
    """Request to store a new event."""

    type: str = Field(..., min_length=1, description="Event type")
    data: dict = Field(default_factory=dict, description="Event data payload")
    timestamp: Optional[int] = Field(default=None, description="Unix timestamp (auto-set if None)")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "app_launch",
                "data": {"app": "instagram", "duration_seconds": 1200},
                "timestamp": 1699888888
            }
        }


class MemoryStoreResponse(BaseModel):
    """Response from storing an event."""

    id: str = Field(..., description="Unique event ID")
    stored: bool = Field(..., description="Success flag")
    embedding_dim: int = Field(..., description="Embedding dimensions")


# ============================================================================
# Memory Search
# ============================================================================


class SearchFilter(BaseModel):
    """Filters for memory search."""

    type: Optional[str] = Field(default=None, description="Filter by event type")
    timestamp_min: Optional[int] = Field(default=None, description="Filter by minimum timestamp")
    timestamp_max: Optional[int] = Field(default=None, description="Filter by maximum timestamp")


class MemorySearchRequest(BaseModel):
    """Request to search memory."""

    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Results limit")
    filters: Optional[SearchFilter] = Field(default=None, description="Optional filters")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "when did i use instagram",
                "limit": 10,
                "filters": {"type": "app_launch"}
            }
        }


class MemorySearchResult(BaseModel):
    """Single search result."""

    id: str = Field(..., description="Event ID")
    type: str = Field(..., description="Event type")
    data: dict = Field(..., description="Event data")
    timestamp: int = Field(..., description="Event timestamp")
    similarity_score: float = Field(..., ge=0, le=1, description="Similarity score")


class MemorySearchResponse(BaseModel):
    """Response from memory search."""

    results: list[MemorySearchResult] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results")
    total: int = Field(..., description="Total matching events")


# ============================================================================
# Memory Recent
# ============================================================================


class MemoryRecentResponse(BaseModel):
    """Response for recent events."""

    results: list[dict] = Field(..., description="Recent events")
    count: int = Field(..., description="Results in this response")
    total: int = Field(..., description="Total events")
    has_more: bool = Field(..., description="More results available")


# ============================================================================
# State Management
# ============================================================================


class MoodUpdateRequest(BaseModel):
    """Request to update mood."""

    mood: str = Field(..., regex="^(happy|sad|focused|tired|anxious|neutral)$", description="Mood value")
    context: Optional[str] = Field(default=None, description="Optional context")

    class Config:
        json_schema_extra = {
            "example": {
                "mood": "focused",
                "context": "Working on backend features"
            }
        }


class MoodUpdateResponse(BaseModel):
    """Response from mood update."""

    mood: str = Field(..., description="Updated mood")
    updated_at: int = Field(..., description="Update timestamp")
    acknowledgement: str = Field(..., description="Acknowledgement message")


class BlogPost(BaseModel):
    """Blog post summary."""

    title: str = Field(..., description="Post title")
    summary: Optional[str] = Field(default=None, description="Post summary")
    url: str = Field(..., description="Post URL")
    published_at: int = Field(..., description="Publication timestamp")
    scraped_at: Optional[int] = Field(default=None, description="Scrape timestamp")


class StateCurrentResponse(BaseModel):
    """Response for current state."""

    mood: str = Field(..., description="Current mood")
    mood_updated_at: int = Field(..., description="Mood update timestamp")
    thoughts: str = Field(..., description="Recent thoughts/summary")
    thoughts_updated_at: int = Field(..., description="Thoughts update timestamp")
    blog_posts: list[BlogPost] = Field(..., description="Recent blog posts")


class StateBlogResponse(BaseModel):
    """Response for blog posts."""

    blog_posts: list[BlogPost] = Field(..., description="Blog posts")
    last_updated: int = Field(..., description="Last update timestamp")
    next_scrape: int = Field(..., description="Next scheduled scrape time")


# ============================================================================
# Device Sync
# ============================================================================


class SyncContext(BaseModel):
    """Sync context information."""

    last_sync: int = Field(..., description="Last sync timestamp")
    new_events_count: int = Field(..., description="Count of new events")
    server_time: int = Field(..., description="Current server time")


class SyncPullRequest(BaseModel):
    """Request to pull sync data."""

    last_sync_timestamp: int = Field(default=0, description="Last sync timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "last_sync_timestamp": 1699777777
            }
        }


class SyncPullResponse(BaseModel):
    """Response from sync pull."""

    current_state: dict = Field(..., description="Current mood/thoughts")
    recent_memories: list[dict] = Field(..., description="Recent events")
    context: SyncContext = Field(..., description="Sync context")


class SyncPushRequest(BaseModel):
    """Request to push events to server."""

    events: list[dict] = Field(..., min_items=1, max_items=100, description="Events to push")

    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "type": "app_launch",
                        "data": {"app": "instagram", "duration_seconds": 1200},
                        "timestamp": 1699888888
                    }
                ]
            }
        }


class SyncPushResult(BaseModel):
    """Result for single pushed event."""

    event_index: int = Field(..., description="Event index in request")
    id: Optional[str] = Field(default=None, description="Stored event ID")
    success: bool = Field(..., description="Success flag")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class SyncPushResponse(BaseModel):
    """Response from sync push."""

    stored_count: int = Field(..., description="Number of stored events")
    failed_count: int = Field(..., description="Number of failed events")
    results: list[SyncPushResult] = Field(..., description="Result for each event")


# ============================================================================
# Authentication
# ============================================================================


class TokenResponse(BaseModel):
    """JWT token response."""

    token: str = Field(..., description="JWT token")
    expires_in: int = Field(..., description="Seconds until expiration")
    token_type: str = Field(default="Bearer", description="Token type")


class RefreshTokenRequest(BaseModel):
    """Request to refresh token."""

    token: str = Field(..., description="Expired or valid JWT")


class RefreshTokenResponse(BaseModel):
    """Response from token refresh."""

    token: str = Field(..., description="New JWT token")
    expires_in: int = Field(..., description="Seconds until expiration")


# ============================================================================
# Error Response
# ============================================================================


class ErrorDetail(BaseModel):
    """Error detail."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(default=None, description="Additional details")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail = Field(..., description="Error information")
    timestamp: int = Field(..., description="Error timestamp")
