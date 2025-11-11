"""Text summarization service using Ollama (local LLM)."""

import logging

import httpx

logger = logging.getLogger(__name__)


class Summarizer:
    """AI-powered text summarization service using Ollama."""

    def __init__(self, ollama_host: str = "http://localhost:11434"):
        """Initialize Ollama client.

        Args:
            ollama_host: Ollama server URL (default: http://localhost:11434)
        """
        self.ollama_host = ollama_host
        self.model = "mistral"  # Using Mistral 7B for best performance on your hardware
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minutes for slower hardware
        logger.info(f"Initialized Summarizer with Ollama (model: {self.model}, host: {ollama_host})")

    async def summarize(self, text: str, max_length: int = 200) -> str:
        """Summarize text using Ollama.

        Args:
            text: Text to summarize
            max_length: Maximum length of summary in words

        Returns:
            Summarized text, or original truncated if API fails
        """
        if not text or len(text.strip()) == 0:
            return ""

        try:
            prompt = f"Summarize this in under {max_length} words, focusing on key points:\n\n{text}"

            response = await self.client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=300.0  # 5 minutes for slower hardware
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API returned {response.status_code}")

            result = response.json()
            summary = result.get("response", "").strip()

            if not summary:
                raise Exception("Empty response from Ollama")

            logger.info(f"Summarized {len(text)} chars to {len(summary)} chars")
            return summary

        except Exception as e:
            logger.warning(f"Ollama summarization failed: {e}, using fallback")
            # Fallback: return first N words
            words = text.split()[:max_length]
            return " ".join(words)

    async def summarize_blog_posts(self, posts: list[dict]) -> list[dict]:
        """Summarize multiple blog posts.

        Args:
            posts: List of blog post dictionaries with 'body' field

        Returns:
            Same posts with 'summary' field added
        """
        summarized = []
        for i, post in enumerate(posts):
            body = post.get("body", "")
            try:
                summary = await self.summarize(body, max_length=200)
                post_with_summary = {**post, "summary": summary}
                summarized.append(post_with_summary)
                logger.info(f"Summarized post {i + 1}/{len(posts)}")
            except Exception as e:
                logger.error(f"Failed to summarize post {i}: {e}")
                # Include original post without summary
                summarized.append(post)

        return summarized

    async def summarize_text_bulk(
        self,
        texts: list[str],
        max_length: int = 200
    ) -> list[str]:
        """Summarize multiple text snippets.

        Args:
            texts: List of texts to summarize
            max_length: Maximum summary length

        Returns:
            List of summaries
        """
        summaries = []
        for i, text in enumerate(texts):
            try:
                summary = await self.summarize(text, max_length=max_length)
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to summarize text {i}: {e}")
                summaries.append("")

        return summaries
