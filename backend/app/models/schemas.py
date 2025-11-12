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

    mood: str = Field(..., pattern="^(happy|sad|focused|tired|anxious|neutral)$", description="Mood value")
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


# ============================================================================
# Captured Text Logs
# ============================================================================


class CapturedTextLogEntry(BaseModel):
    """Single captured text log entry from device."""

    text: str = Field(..., min_length=1, description="Redacted captured text")
    appPackage: str = Field(..., description="Source app package (e.g., com.instagram.android)")
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    deviceId: str = Field(default="unknown", description="Device identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "hey how are you doing",
                "appPackage": "com.instagram.android",
                "timestamp": 1699888888000,
                "deviceId": "pixel-7-abc123"
            }
        }


class CapturedTextLogsUploadRequest(BaseModel):
    """Request to upload batch of captured text logs."""

    logs: list[CapturedTextLogEntry] = Field(
        ..., min_items=1, max_items=200, description="Batch of text logs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "logs": [
                    {
                        "text": "working on features",
                        "appPackage": "com.vscode",
                        "timestamp": 1699888900000,
                        "deviceId": "pixel-7-abc123"
                    },
                    {
                        "text": "lets grab coffee",
                        "appPackage": "com.instagram.android",
                        "timestamp": 1699888905000,
                        "deviceId": "pixel-7-abc123"
                    }
                ]
            }
        }


class CapturedTextLogsUploadResponse(BaseModel):
    """Response from text logs upload."""

    uploaded: int = Field(..., ge=0, description="Number of logs uploaded")
    failed: int = Field(..., ge=0, description="Number of logs that failed")
    status: str = Field(..., description="Overall status (success/partial/failed)")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "uploaded": 15,
                "failed": 0,
                "status": "success",
                "message": "15 logs stored successfully"
            }
        }


class CapturedTextLogsSearchRequest(BaseModel):
    """Request to search captured text logs."""

    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=20, ge=1, le=100, description="Results limit")
    appPackage: Optional[str] = Field(default=None, description="Filter by app package")
    timestamp_min: Optional[int] = Field(default=None, description="Minimum timestamp (ms)")
    timestamp_max: Optional[int] = Field(default=None, description="Maximum timestamp (ms)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "instagram messages",
                "limit": 20,
                "appPackage": "com.instagram.android"
            }
        }


class CapturedTextLogsSearchResult(BaseModel):
    """Single search result from text logs."""

    id: str = Field(..., description="Log entry ID")
    text: str = Field(..., description="Captured text")
    appPackage: str = Field(..., description="Source app package")
    timestamp: int = Field(..., description="Timestamp (ms)")
    deviceId: str = Field(..., description="Device ID")
    similarity_score: Optional[float] = Field(default=None, ge=0, le=1, description="Similarity score")


class CapturedTextLogsSearchResponse(BaseModel):
    """Response from text logs search."""

    results: list[CapturedTextLogsSearchResult] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results")
    total: int = Field(..., description="Total matching entries")
