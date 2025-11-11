"""Event type definitions from Android app."""

import time
from typing import Optional, Union
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base event class."""

    type: str = Field(..., description="Event type")
    timestamp: Optional[int] = Field(default_factory=lambda: int(time.time()), description="Unix timestamp")
    device_id: Optional[str] = Field(default="unknown", description="Device ID")


class AppLaunchEvent(BaseEvent):
    """App launch event."""

    type: str = Field("app_launch", frozen=True)
    data: dict = Field(
        default_factory=lambda: {"app": "", "duration_seconds": 0},
        description="App launch data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "app_launch",
                "data": {"app": "instagram", "duration_seconds": 1200},
                "timestamp": 1699888888,
                "device_id": "device-001"
            }
        }


class NotificationEvent(BaseEvent):
    """Notification received event."""

    type: str = Field("notification", frozen=True)
    data: dict = Field(
        default_factory=lambda: {"source": "", "subject": ""},
        description="Notification data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "notification",
                "data": {"source": "gmail", "subject": "Important email"},
                "timestamp": 1699888888,
                "device_id": "device-001"
            }
        }


class MiniGameCompleteEvent(BaseEvent):
    """Mini-game completion event."""

    type: str = Field("minigame_complete", frozen=True)
    data: dict = Field(
        default_factory=lambda: {"game_type": "", "success": False},
        description="Mini-game completion data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "minigame_complete",
                "data": {"game_type": "math_quiz", "success": True},
                "timestamp": 1699888888,
                "device_id": "device-001"
            }
        }


class UserInteractionEvent(BaseEvent):
    """User interaction event."""

    type: str = Field("user_interaction", frozen=True)
    data: dict = Field(
        default_factory=dict,
        description="Interaction data (taps, swipes, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "user_interaction",
                "data": {"action": "message_tapped", "message_id": "msg-123"},
                "timestamp": 1699888888,
                "device_id": "device-001"
            }
        }


class AvatarMoodChangeEvent(BaseEvent):
    """Avatar mood change event."""

    type: str = Field("avatar_mood_change", frozen=True)
    data: dict = Field(
        default_factory=lambda: {"mood": "neutral"},
        description="Avatar mood data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "avatar_mood_change",
                "data": {"mood": "happy"},
                "timestamp": 1699888888,
                "device_id": "device-001"
            }
        }


# Union of all event types
AppEvent = Union[
    AppLaunchEvent,
    NotificationEvent,
    MiniGameCompleteEvent,
    UserInteractionEvent,
    AvatarMoodChangeEvent,
]

# Event type registry
EVENT_TYPES = {
    "app_launch": AppLaunchEvent,
    "notification": NotificationEvent,
    "minigame_complete": MiniGameCompleteEvent,
    "user_interaction": UserInteractionEvent,
    "avatar_mood_change": AvatarMoodChangeEvent,
}


def create_event(
    type_str: str,
    data: dict,
    timestamp: Optional[int] = None,
    device_id: str = "unknown"
) -> BaseEvent:
    """Factory for creating events by type.

    Args:
        type_str: Event type string
        data: Event data payload
        timestamp: Unix timestamp (auto-set if None)
        device_id: Device ID

    Returns:
        Event instance of appropriate type

    Raises:
        ValueError: If event type is unknown
    """
    event_class = EVENT_TYPES.get(type_str)
    if not event_class:
        raise ValueError(f"Unknown event type: {type_str}")

    return event_class(
        type=type_str,
        data=data,
        timestamp=timestamp or int(time.time()),
        device_id=device_id
    )


def validate_event(event_data: dict) -> BaseEvent:
    """Validate and create event from raw data.

    Args:
        event_data: Raw event dictionary

    Returns:
        Validated event instance

    Raises:
        ValueError: If event data is invalid
    """
    type_str = event_data.get("type")
    if not type_str:
        raise ValueError("Event must have 'type' field")

    return create_event(
        type_str=type_str,
        data=event_data.get("data", {}),
        timestamp=event_data.get("timestamp"),
        device_id=event_data.get("device_id", "unknown")
    )
