"""Service for generating periodic life commentary."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from app.models.commentary import CommentaryMetadata, CommentaryResponse
from app.prompts.commentary_prompts import format_commentary_prompt
from app.services.log_accumulator import LogAccumulator
from app.services.state_manager import StateManager
from app.services.summarizer import Summarizer

logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_DAYS_OF_DATA = 3
DEFAULT_WEEKS_OF_BLOGS = 2


class CommentaryService:
    """Generates LLM-based commentary on life patterns and activities."""

    def __init__(
        self,
        log_accumulator: LogAccumulator,
        state_manager: StateManager,
        summarizer: Summarizer
    ):
        """Initialize commentary service.

        Args:
            log_accumulator: Service for accessing accumulated logs
            state_manager: Service for accessing blog posts
            summarizer: LLM service for generating commentary
        """
        self.log_accumulator = log_accumulator
        self.state_manager = state_manager
        self.summarizer = summarizer

    async def generate_commentary(
        self,
        days_of_data: int,
        weeks_of_blogs: int,
        prompt: str,
        prompt_index: int = 0
    ) -> CommentaryResponse:
        """Generate commentary based on recent logs and blog posts.

        Args:
            days_of_data: Number of past days of log data to analyze
            weeks_of_blogs: Number of weeks of blog posts to include
            prompt: Commentary prompt template to use
            prompt_index: Index of the prompt being used (for metadata)

        Returns:
            CommentaryResponse with generated commentary and metadata
        """
        logger.info(
            f"Generating commentary with {days_of_data} days of data, "
            f"{weeks_of_blogs} weeks of blogs, prompt index {prompt_index}"
        )

        # Gather log data from recent days
        logs_data, log_count = await self._gather_recent_logs(days_of_data)

        # Gather blog posts from recent weeks
        blog_data, blog_count = await self._gather_recent_blogs(weeks_of_blogs)

        # Check if we have any data
        if not logs_data and not blog_data:
            logger.warning("No data available for commentary generation")
            return CommentaryResponse(
                commentary="No data available for commentary. Please check back later when more activity has been logged.",
                metadata=CommentaryMetadata(
                    generated_at=datetime.now().isoformat(),
                    prompt_index=prompt_index,
                    days_analyzed=days_of_data,
                    weeks_analyzed=weeks_of_blogs,
                    log_count=0,
                    blog_count=0
                )
            )

        # Format the prompt with data
        formatted_prompt = format_commentary_prompt(prompt, logs_data, blog_data)

        # Generate commentary using LLM
        try:
            commentary = await self.summarizer.generate_text(
                prompt=formatted_prompt,
                max_tokens=2000  # Reasonable length for periodic commentary
            )
        except Exception as e:
            logger.error(f"Failed to generate commentary with LLM: {e}", exc_info=True)
            commentary = f"Error generating commentary: {str(e)}"

        # Build response with metadata
        return CommentaryResponse(
            commentary=commentary,
            metadata=CommentaryMetadata(
                generated_at=datetime.now().isoformat(),
                prompt_index=prompt_index,
                days_analyzed=days_of_data,
                weeks_analyzed=weeks_of_blogs,
                log_count=log_count,
                blog_count=blog_count
            )
        )

    async def _gather_recent_logs(self, days: int) -> tuple[str, int]:
        """Gather log data from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Tuple of (combined_logs_string, total_log_count)
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days - 1)  # -1 because today counts as day 1

            # Get logs for each day in range
            date_range_logs = self.log_accumulator.get_date_range_logs(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            # Combine all logs with date headers
            sections = []
            total_count = 0

            for date_str in sorted(date_range_logs.keys()):
                log_content = date_range_logs[date_str]
                if log_content and log_content.strip():
                    sections.append(f"=== {date_str} ===")
                    sections.append(log_content)
                    sections.append("")  # Blank line between days

                    # Count non-empty lines
                    total_count += len([line for line in log_content.split("\n") if line.strip()])

            combined = "\n".join(sections) if sections else ""

            logger.info(f"Gathered {total_count} log entries from last {days} days")
            return combined, total_count

        except Exception as e:
            logger.error(f"Failed to gather recent logs: {e}", exc_info=True)
            return "", 0

    async def _gather_recent_blogs(self, weeks: int) -> tuple[str, int]:
        """Gather blog posts from the last N weeks.

        Args:
            weeks: Number of weeks to look back

        Returns:
            Tuple of (combined_blogs_string, total_blog_count)
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(weeks=weeks)

            # Get all cached blog posts
            thoughts_data = await self.state_manager.get_recent_thoughts()
            all_posts = thoughts_data.get("blog_posts", [])

            # Filter to posts within the time range
            start_timestamp = start_date.timestamp()
            end_timestamp = end_date.timestamp()

            filtered_posts = []
            for post in all_posts:
                if post.get("published_at"):
                    if start_timestamp <= post["published_at"] <= end_timestamp:
                        filtered_posts.append(post)

            # Sort by published date (newest first)
            filtered_posts.sort(key=lambda p: p.get("published_at", 0), reverse=True)

            # Format posts as text
            sections = []
            for post in filtered_posts:
                sections.append(f"Title: {post['title']}")
                sections.append(f"URL: {post['url']}")
                sections.append(f"Published: {self._format_timestamp(post['published_at'])}")
                sections.append(f"\n{post['body']}\n")
                sections.append("-" * 60)

            combined = "\n".join(sections) if sections else ""
            blog_count = len(filtered_posts)

            logger.info(f"Gathered {blog_count} blog posts from last {weeks} weeks")
            return combined, blog_count

        except Exception as e:
            logger.error(f"Failed to gather recent blogs: {e}", exc_info=True)
            return "", 0

    def _format_timestamp(self, timestamp: int) -> str:
        """Format Unix timestamp to readable string.

        Args:
            timestamp: Unix timestamp

        Returns:
            Formatted date string
        """
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "Unknown"
