"""Blog scraping service."""

import logging
import time
from typing import Optional

import feedparser
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)


class BlogScraper:
    """Service for fetching and parsing blog posts."""

    def __init__(self, blog_url: str):
        """Initialize blog scraper.

        Args:
            blog_url: Blog homepage URL
        """
        self.blog_url = blog_url
        self.timeout = 10

    async def fetch_and_parse(self) -> list[dict]:
        """Scrape blog and return structured posts.

        Returns:
            List of blog posts with title, body, url, published_at
        """
        logger.info(f"Starting blog scrape from {self.blog_url}")

        # Try RSS first (cleaner)
        posts = await self._fetch_rss()
        if posts:
            logger.info(f"Fetched {len(posts)} posts from RSS")
            return posts

        # Fallback to HTML scraping
        logger.info("RSS not available, falling back to HTML scraping")
        posts = await self._fetch_html()
        logger.info(f"Fetched {len(posts)} posts from HTML")
        return posts

    async def _fetch_rss(self) -> list[dict]:
        """Try to parse RSS feed.

        Returns:
            List of blog posts, or empty list if RSS not available
        """
        try:
            feed_urls = [
                f"{self.blog_url}/feed.xml",
                f"{self.blog_url}/feed.json",
                f"{self.blog_url}/rss",
                f"{self.blog_url}/feed",
            ]

            for feed_url in feed_urls:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(feed_url)
                        response.raise_for_status()

                    feed = feedparser.parse(response.text)
                    if feed.entries:
                        posts = []
                        for entry in feed.entries[:10]:  # Last 10 posts
                            posts.append({
                                "title": entry.get("title", "Untitled"),
                                "body": entry.get("summary", ""),
                                "url": entry.get("link", self.blog_url),
                                "published_at": self._parse_date(entry.get("published", int(time.time()))),
                                "scraped_at": int(time.time())
                            })
                        return posts

                except Exception as e:
                    logger.debug(f"RSS feed at {feed_url} not available: {e}")
                    continue

            return []

        except Exception as e:
            logger.warning(f"RSS parsing failed: {e}")
            return []

    async def _fetch_html(self) -> list[dict]:
        """Parse HTML if no RSS available.

        Returns:
            List of blog posts extracted from HTML
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.blog_url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            posts = []

            # Find post containers (adjust selectors for your blog)
            for article in soup.find_all(["article", "div.post", "div.blog-post"]):
                title_elem = article.find(["h1", "h2", "h3"])
                link_elem = article.find("a")

                if title_elem and link_elem:
                    title = title_elem.get_text().strip()
                    url = link_elem.get("href", "")

                    # Make absolute URL if relative
                    if url and not url.startswith("http"):
                        url = f"{self.blog_url.rstrip('/')}/{url.lstrip('/')}"

                    # Extract body text (first 500 chars)
                    body_text = article.get_text()[:500]

                    posts.append({
                        "title": title,
                        "body": body_text,
                        "url": url,
                        "published_at": int(time.time()),
                        "scraped_at": int(time.time())
                    })

            return posts

        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            return []

    def _parse_date(self, date_str: Optional[str]) -> int:
        """Convert string date to Unix timestamp.

        Args:
            date_str: Date string

        Returns:
            Unix timestamp
        """
        if not date_str:
            return int(time.time())

        try:
            # Handle tuple format from feedparser
            if isinstance(date_str, tuple):
                import calendar
                return calendar.timegm(date_str)

            # Parse ISO format or common formats
            dt = dateutil_parser.parse(str(date_str))
            return int(dt.timestamp())

        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return int(time.time())
