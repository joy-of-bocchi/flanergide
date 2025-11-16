"""Pydantic models for summarization system."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DailySummaryRequest(BaseModel):
    """Request model for daily summary."""

    date: Optional[str] = Field(
        None,
        description="Date in YYYY-MM-DD format. If not provided, defaults to yesterday.",
        example="2025-11-15"
    )


class WeeklySummaryRequest(BaseModel):
    """Request model for weekly summary."""

    start_date: Optional[str] = Field(
        None,
        description="Start date in YYYY-MM-DD format. If not provided, defaults to 7 days ago.",
        example="2025-11-09"
    )
    end_date: Optional[str] = Field(
        None,
        description="End date in YYYY-MM-DD format. If not provided, defaults to today.",
        example="2025-11-15"
    )


class SummaryMetadata(BaseModel):
    """Metadata about generated summary."""

    generated_at: str = Field(..., description="Timestamp when summary was generated")
    date_range: str = Field(..., description="Date or date range analyzed")
    log_count: int = Field(..., description="Number of text logs analyzed")
    blog_count: int = Field(..., description="Number of blog posts included")
    analysis_type: str = Field(..., description="Type of analysis: daily or weekly")


class SummaryResponse(BaseModel):
    """Response model for summary endpoints."""

    summary: str = Field(..., description="Generated summary in markdown format")
    metadata: SummaryMetadata = Field(..., description="Metadata about the analysis")
    log_file_path: str = Field(..., description="Path to accumulated log file")
    summary_file_path: str = Field(..., description="Path to saved summary markdown file")


class SummarySection(BaseModel):
    """Individual section of summary (for future structured output)."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")


class StructuredSummary(BaseModel):
    """Structured summary with separate sections (future enhancement)."""

    activities: str = Field(..., description="What you did")
    thoughts: str = Field(..., description="What was on your mind")
    mood: str = Field(..., description="Mood analysis")
    personality: str = Field(..., description="Personality insights")
    metadata: SummaryMetadata = Field(..., description="Metadata")
