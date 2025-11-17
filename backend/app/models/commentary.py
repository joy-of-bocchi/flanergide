"""Pydantic models for commentary system."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CommentaryRequest(BaseModel):
    """Request model for commentary generation."""

    days_of_data: int = Field(
        3,
        description="Number of past days of log data to analyze",
        ge=1,
        le=30,
        example=3
    )
    weeks_of_blogs: int = Field(
        2,
        description="Number of weeks of blog posts to include",
        ge=1,
        le=12,
        example=2
    )
    prompt: str = Field(
        ...,
        description="Commentary prompt template to use for generation",
        min_length=10
    )


class CommentaryMetadata(BaseModel):
    """Metadata about generated commentary."""

    generated_at: str = Field(..., description="Timestamp when commentary was generated")
    prompt_index: int = Field(..., description="Index of the prompt used (0-9 for round-robin)")
    days_analyzed: int = Field(..., description="Number of days of data analyzed")
    weeks_analyzed: int = Field(..., description="Number of weeks of blog posts analyzed")
    log_count: int = Field(..., description="Number of text logs analyzed")
    blog_count: int = Field(..., description="Number of blog posts included")


class CommentaryResponse(BaseModel):
    """Response model for commentary endpoints."""

    commentary: str = Field(..., description="Generated commentary text")
    metadata: CommentaryMetadata = Field(..., description="Metadata about the generation")
