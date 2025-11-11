"""Short-term memory state management service."""

import json
import logging
import os
import tempfile
import time
from typing import Optional, Union

logger = logging.getLogger(__name__)


class StateManager:
    """Service for managing short-term memory state files."""

    VALID_MOODS = {"happy", "sad", "focused", "tired", "anxious", "neutral"}

    def __init__(self, state_dir: str):
        """Initialize state manager.

        Args:
            state_dir: Directory for state files
        """
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

        self.mood_file = os.path.join(state_dir, "current_mood.txt")
        self.thoughts_file = os.path.join(state_dir, "recent_thoughts.txt")
        self.blog_cache_file = os.path.join(state_dir, "blog_cache.json")

        # Initialize files if they don't exist
        self._init_files()
        logger.info(f"Initialized StateManager at {state_dir}")

    def _init_files(self):
        """Initialize state files if they don't exist."""
        if not os.path.exists(self.mood_file):
            self._atomic_write_json(
                self.mood_file,
                {"mood": "neutral", "updated_at": 0, "context": ""}
            )

        if not os.path.exists(self.thoughts_file):
            with open(self.thoughts_file, "w") as f:
                f.write("")

        if not os.path.exists(self.blog_cache_file):
            self._atomic_write_json(self.blog_cache_file, [])

    async def get_current_mood(self) -> dict:
        """Read current mood from file.

        Returns:
            Mood dictionary with mood, updated_at, context
        """
        try:
            if not os.path.exists(self.mood_file):
                return {"mood": "neutral", "updated_at": 0, "context": ""}

            with open(self.mood_file, "r") as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(f"Failed to read mood file: {e}")
            return {"mood": "neutral", "updated_at": 0, "context": ""}

    async def update_mood(self, mood: str, context: Optional[str] = None) -> dict:
        """Write new mood to file.

        Args:
            mood: New mood value
            context: Optional context

        Returns:
            Updated mood dictionary

        Raises:
            ValueError: If mood is invalid
        """
        if mood not in self.VALID_MOODS:
            raise ValueError(f"Invalid mood: {mood}. Must be one of {self.VALID_MOODS}")

        data = {
            "mood": mood,
            "updated_at": int(time.time()),
            "context": context or ""
        }

        try:
            self._atomic_write_json(self.mood_file, data)
            logger.info(f"Updated mood to {mood}")
            return data
        except Exception as e:
            logger.error(f"Failed to update mood: {e}")
            raise

    async def get_recent_thoughts(self) -> dict:
        """Read recent thoughts and blog summaries.

        Returns:
            Dictionary with thoughts, blog_posts, updated_at
        """
        thoughts = ""
        blog_posts = []
        updated_at = 0

        try:
            if os.path.exists(self.thoughts_file):
                with open(self.thoughts_file, "r") as f:
                    thoughts = f.read()
                updated_at = int(os.path.getmtime(self.thoughts_file))

            if os.path.exists(self.blog_cache_file):
                with open(self.blog_cache_file, "r") as f:
                    blog_posts = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read thoughts: {e}")

        return {
            "thoughts": thoughts,
            "blog_posts": blog_posts,
            "updated_at": updated_at
        }

    async def update_blog_cache(
        self,
        posts: list[dict],
        summarizer=None
    ) -> bool:
        """Update blog post cache and thoughts summary.

        Args:
            posts: List of new blog posts to add
            summarizer: Optional summarizer service for summaries

        Returns:
            True if successful
        """
        try:
            logger.info(f"[BlogCache] Starting update with {len(posts)} posts")

            # Load existing cached posts
            existing_posts = []
            if os.path.exists(self.blog_cache_file):
                try:
                    with open(self.blog_cache_file, "r") as f:
                        existing_posts = json.load(f)
                    logger.debug(f"[BlogCache] Loaded {len(existing_posts)} existing posts from cache")
                except Exception as e:
                    logger.warning(f"[BlogCache] Could not load existing cache: {e}")

            # Merge new posts with existing (deduplicate by URL)
            existing_urls = {post.get("url") for post in existing_posts}
            new_posts = [post for post in posts if post.get("url") not in existing_urls]

            if not new_posts:
                logger.info("[BlogCache] No new posts to add, cache unchanged")
                return True

            logger.info(f"[BlogCache] Adding {len(new_posts)} new posts to cache")

            # Summarize only new posts if summarizer provided
            if summarizer:
                logger.info(f"[BlogCache] Summarizing {len(new_posts)} new posts using AI...")
                new_posts = await summarizer.summarize_blog_posts(new_posts)
                logger.info(f"[BlogCache] ✓ Summarization complete")
            else:
                logger.debug("[BlogCache] No summarizer provided, skipping summarization")

            # Merge: new posts first, then existing (sorted by timestamp, newest first)
            all_posts = new_posts + existing_posts
            all_posts.sort(key=lambda p: p.get("scraped_at", 0), reverse=True)

            # Keep only last 50 posts to prevent unbounded growth
            all_posts = all_posts[:50]

            # Cache merged posts
            logger.debug(f"[BlogCache] Writing {len(all_posts)} total posts to {self.blog_cache_file}")
            self._atomic_write_json(self.blog_cache_file, all_posts)
            logger.info(f"[BlogCache] ✓ Cache file written")

            # Update thoughts file with latest summaries (last 5 posts)
            summaries = []
            for i, post in enumerate(all_posts[:5]):
                title = post.get("title", "Untitled")
                summary = post.get("summary", post.get("body", "")[:200])
                url = post.get("url", "")

                summaries.append(f"**{title}**\n{summary}\n[Read more]({url})")
                logger.debug(f"[BlogCache]   Post {i+1}: {title}")

            thoughts_text = "\n\n".join(summaries)

            logger.debug(f"[BlogCache] Writing thoughts to {self.thoughts_file}")
            with open(self.thoughts_file, "w") as f:
                f.write(thoughts_text)

            logger.info(f"[BlogCache] ✓ Successfully updated blog cache ({len(new_posts)} new, {len(all_posts)} total)")
            return True

        except Exception as e:
            logger.error(f"[BlogCache] ✗ Failed to update blog cache: {type(e).__name__} - {e}", exc_info=True)
            return False

    async def get_current_state(self) -> dict:
        """Get combined current state (mood + thoughts + blog).

        Returns:
            Dictionary with all current state
        """
        mood_data = await self.get_current_mood()
        thoughts_data = await self.get_recent_thoughts()

        return {
            "mood": mood_data.get("mood", "neutral"),
            "mood_updated_at": mood_data.get("updated_at", 0),
            "mood_context": mood_data.get("context", ""),
            "thoughts": thoughts_data.get("thoughts", ""),
            "thoughts_updated_at": thoughts_data.get("updated_at", 0),
            "blog_posts": thoughts_data.get("blog_posts", [])
        }

    def _atomic_write_json(self, filepath: str, data: Union[dict, list]):
        """Write JSON atomically using temp file.

        Args:
            filepath: Path to write to
            data: Data to write

        Raises:
            Exception: If write fails
        """
        try:
            # Write to temp file in same directory
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=os.path.dirname(filepath),
                delete=False,
                suffix=".tmp"
            ) as tmp:
                json.dump(data, tmp, indent=2)
                tmp_path = tmp.name

            # Atomic rename
            os.replace(tmp_path, filepath)

        except Exception as e:
            logger.error(f"Atomic write failed for {filepath}: {e}")
            # Cleanup temp file if it exists
            try:
                if "tmp_path" in locals():
                    os.unlink(tmp_path)
            except:
                pass
            raise

    def cleanup_old_state(self, days: int = 30):
        """Cleanup old state data (optional).

        Args:
            days: Only keep state files modified within last N days
        """
        cutoff = time.time() - (days * 86400)

        for filepath in [self.thoughts_file, self.blog_cache_file]:
            if os.path.exists(filepath):
                mtime = os.path.getmtime(filepath)
                if mtime < cutoff:
                    logger.info(f"Removing old state file: {filepath}")
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        logger.warning(f"Failed to remove {filepath}: {e}")
