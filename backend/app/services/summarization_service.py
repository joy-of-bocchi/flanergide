"""Service for generating daily and weekly summaries."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.prompts.summarization_prompts import format_daily_prompt, format_weekly_prompt
from app.services.log_accumulator import LogAccumulator
from app.services.state_manager import StateManager
from app.services.summarizer import Summarizer

logger = logging.getLogger(__name__)


class SummarizationService:
    """Generates LLM-based summaries on daily and weekly activity."""

    def __init__(
        self,
        log_accumulator: LogAccumulator,
        state_manager: StateManager,
        summarizer: Summarizer,
        analysis_dir: str
    ):
        """Initialize summarization service.

        Args:
            log_accumulator: Service for accessing accumulated logs
            state_manager: Service for accessing blog posts
            summarizer: LLM service for generating summary
            analysis_dir: Base directory for analysis files
        """
        self.log_accumulator = log_accumulator
        self.state_manager = state_manager
        self.summarizer = summarizer
        self.analysis_dir = Path(analysis_dir)

    async def generate_daily_summary(
        self,
        date: Optional[str] = None
    ) -> dict:
        """Generate daily summary for a specific date.

        Args:
            date: Date in YYYY-MM-DD format. If None, uses yesterday.

        Returns:
            Dictionary with summary, metadata, and file paths
        """
        # Default to yesterday if no date provided
        if date is None:
            yesterday = datetime.now() - timedelta(days=1)
            date = yesterday.strftime("%Y-%m-%d")

        logger.info(f"Generating daily summary for {date}")

        # Gather data
        log_content = self.log_accumulator.get_log_content(date)
        log_count = self.log_accumulator.get_log_count(date)
        blog_posts = await self._get_blog_posts_for_date(date)
        blog_count = len(blog_posts)

        # Check if we have any data
        if not log_content and not blog_posts:
            logger.warning(f"No data found for {date}")
            return {
                "summary": f"# No Data Available\n\nNo phone logs or blog posts found for {date}.",
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "date_range": date,
                    "log_count": 0,
                    "blog_count": 0,
                    "analysis_type": "daily"
                },
                "log_file_path": str(self.log_accumulator.get_daily_log_path(date)),
                "summary_file_path": ""
            }

        # Build combined data for LLM
        combined_data = self._build_daily_data(date, log_content, blog_posts)

        # Generate summary using LLM
        prompt = format_daily_prompt(date, combined_data)
        summary = await self._generate_with_llm(prompt, analysis_type="daily")

        # Save summary to file
        summary_path = self._save_summary(date, summary, is_weekly=False)

        # Build response
        return {
            "summary": summary,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "date_range": date,
                "log_count": log_count,
                "blog_count": blog_count,
                "analysis_type": "daily"
            },
            "log_file_path": str(self.log_accumulator.get_daily_log_path(date)),
            "summary_file_path": str(summary_path)
        }

    async def generate_today_summary(self) -> dict:
        """Generate summary for today (in-progress day).

        Returns:
            Dictionary with summary, metadata, and file paths
        """
        today = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Generating today's summary for {today}")

        # Use same logic as daily, but for today
        result = await self.generate_daily_summary(date=today)

        # Update analysis type to indicate it's today
        result["metadata"]["analysis_type"] = "today"

        # Add note to summary that it's in-progress
        note = "\n\n---\n*Note: This is an in-progress analysis for today. Data may be incomplete.*\n"
        result["summary"] = result["summary"] + note

        return result

    async def generate_weekly_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """Generate weekly summary for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format. If None, uses 7 days ago.
            end_date: End date in YYYY-MM-DD format. If None, uses today.

        Returns:
            Dictionary with summary, metadata, and file paths
        """
        # Default to last 7 days
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if start_date is None:
            start_dt = datetime.now() - timedelta(days=7)
            start_date = start_dt.strftime("%Y-%m-%d")

        logger.info(f"Generating weekly summary for {start_date} to {end_date}")

        # Create weekly log file (combines all daily logs)
        weekly_log_path = self.log_accumulator.create_weekly_log_file(start_date, end_date)

        # Read weekly log content
        with open(weekly_log_path, "r", encoding="utf-8") as f:
            log_content = f.read()

        # Get blog posts for the week
        blog_posts = await self._get_blog_posts_for_range(start_date, end_date)
        blog_count = len(blog_posts)

        # Count total logs
        daily_logs = self.log_accumulator.get_date_range_logs(start_date, end_date)
        total_log_count = sum(
            len([line for line in content.split("\n") if line.strip()])
            for content in daily_logs.values()
        )

        # Check if we have any data
        if not log_content.strip() and not blog_posts:
            logger.warning(f"No data found for {start_date} to {end_date}")
            return {
                "summary": f"# No Data Available\n\nNo phone logs or blog posts found for {start_date} to {end_date}.",
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "date_range": f"{start_date} to {end_date}",
                    "log_count": 0,
                    "blog_count": 0,
                    "analysis_type": "weekly"
                },
                "log_file_path": str(weekly_log_path),
                "summary_file_path": ""
            }

        # Build combined data for LLM
        combined_data = self._build_weekly_data(start_date, end_date, log_content, blog_posts)

        # Generate summary using LLM
        prompt = format_weekly_prompt(start_date, end_date, combined_data)
        summary = await self._generate_with_llm(prompt, analysis_type="weekly")

        # Save summary to file
        date_range_str = f"{start_date}_to_{end_date}"
        summary_path = self._save_summary(date_range_str, summary, is_weekly=True)

        # Build response
        return {
            "summary": summary,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "date_range": f"{start_date} to {end_date}",
                "log_count": total_log_count,
                "blog_count": blog_count,
                "analysis_type": "weekly"
            },
            "log_file_path": str(weekly_log_path),
            "summary_file_path": str(summary_path)
        }

    def _build_daily_data(
        self,
        date: str,
        log_content: Optional[str],
        blog_posts: list[dict]
    ) -> str:
        """Build combined data string for daily analysis.

        Args:
            date: Date being analyzed
            log_content: Content from daily.log file
            blog_posts: List of blog posts from that day

        Returns:
            Formatted string with all data
        """
        sections = []

        # Add phone logs section
        if log_content:
            sections.append("PHONE ACTIVITY LOGS:")
            sections.append(log_content)
        else:
            sections.append("PHONE ACTIVITY LOGS: None")

        # Add blog posts section
        if blog_posts:
            sections.append("\n" + "="*60)
            sections.append("BLOG POSTS:")
            sections.append("="*60 + "\n")

            for post in blog_posts:
                sections.append(f"Title: {post['title']}")
                sections.append(f"URL: {post['url']}")
                sections.append(f"Published: {self._format_timestamp(post['published_at'])}")
                sections.append(f"\nContent:\n{post['body']}\n")
                sections.append("-" * 60 + "\n")
        else:
            sections.append("\nBLOG POSTS: None")

        return "\n".join(sections)

    def _build_weekly_data(
        self,
        start_date: str,
        end_date: str,
        log_content: str,
        blog_posts: list[dict]
    ) -> str:
        """Build combined data string for weekly analysis.

        Args:
            start_date: Start date
            end_date: End date
            log_content: Content from weekly.log file (already has daily separators)
            blog_posts: List of blog posts from that week

        Returns:
            Formatted string with all data
        """
        sections = []

        # Add phone logs section (already formatted by weekly log file)
        sections.append("PHONE ACTIVITY LOGS (BY DAY):")
        sections.append(log_content)

        # Add blog posts section
        if blog_posts:
            sections.append("\n" + "="*60)
            sections.append("BLOG POSTS:")
            sections.append("="*60 + "\n")

            for post in blog_posts:
                sections.append(f"Title: {post['title']}")
                sections.append(f"URL: {post['url']}")
                sections.append(f"Published: {self._format_timestamp(post['published_at'])}")
                sections.append(f"\nContent:\n{post['body']}\n")
                sections.append("-" * 60 + "\n")
        else:
            sections.append("\nBLOG POSTS: None")

        return "\n".join(sections)

    async def _get_blog_posts_for_date(self, date: str) -> list[dict]:
        """Get blog posts published on a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            List of blog post dictionaries
        """
        try:
            # Get all cached blog posts from state manager
            thoughts_data = await self.state_manager.get_recent_thoughts()
            all_posts = thoughts_data.get("blog_posts", [])

            # Filter to posts published on this date
            target_date = datetime.strptime(date, "%Y-%m-%d").date()

            filtered_posts = []
            for post in all_posts:
                if post.get("published_at"):
                    post_date = datetime.fromtimestamp(post["published_at"]).date()
                    if post_date == target_date:
                        filtered_posts.append(post)

            logger.info(f"Found {len(filtered_posts)} blog posts for {date}")
            return filtered_posts

        except Exception as e:
            logger.error(f"Failed to get blog posts for {date}: {e}")
            return []

    async def _get_blog_posts_for_range(self, start_date: str, end_date: str) -> list[dict]:
        """Get blog posts published within a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of blog post dictionaries
        """
        try:
            # Get all cached blog posts from state manager
            thoughts_data = await self.state_manager.get_recent_thoughts()
            all_posts = thoughts_data.get("blog_posts", [])

            # Filter to posts published in this range
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

            filtered_posts = []
            for post in all_posts:
                if post.get("published_at"):
                    post_date = datetime.fromtimestamp(post["published_at"]).date()
                    if start_dt <= post_date <= end_dt:
                        filtered_posts.append(post)

            logger.info(f"Found {len(filtered_posts)} blog posts for {start_date} to {end_date}")
            return filtered_posts

        except Exception as e:
            logger.error(f"Failed to get blog posts for range: {e}")
            return []

    async def _generate_with_llm(self, prompt: str, analysis_type: str) -> str:
        """Generate summary using LLM.

        Args:
            prompt: Formatted prompt with data
            analysis_type: Type of analysis (daily, weekly)

        Returns:
            Generated summary markdown
        """
        try:
            logger.info(f"Generating {analysis_type} commentary with LLM")

            # Use summarizer's Ollama client
            # For commentary, we want longer output than typical summaries
            summary = await self.summarizer.generate_text(
                prompt=prompt,
                max_tokens=4000  # Allow longer analysis
            )

            return summary

        except Exception as e:
            logger.error(f"Failed to generate commentary with LLM: {e}", exc_info=True)

            # Return error message
            return f"""# Summary Generation Failed

An error occurred while generating the summary: {str(e)}

Please check the logs and try again. The accumulated data is still available in the log files.
"""

    def _save_summary(
        self,
        date_or_range: str,
        commentary: str,
        is_weekly: bool
    ) -> Path:
        """Save summary to markdown file.

        Args:
            date_or_range: Date (YYYY-MM-DD) or range (YYYY-MM-DD_to_YYYY-MM-DD)
            commentary: Generated summary markdown
            is_weekly: Whether this is weekly or daily summary

        Returns:
            Path to saved commentary file
        """
        try:
            # Determine directory
            if is_weekly:
                summary_dir = self.analysis_dir / date_or_range
            else:
                summary_dir = self.analysis_dir / date_or_range

            summary_dir.mkdir(parents=True, exist_ok=True)

            # Save to summary.md
            summary_path = summary_dir / "summary.md"

            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(commentary)

            logger.info(f"Saved summary to {summary_path}")
            return summary_path

        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
            # Return empty path if save fails
            return Path("")

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
