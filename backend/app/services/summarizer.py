"""Text summarization service using OpenAI."""

import logging

import openai

logger = logging.getLogger(__name__)


class Summarizer:
    """AI-powered text summarization service."""

    def __init__(self, api_key: str):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        openai.api_key = api_key
        logger.info("Initialized Summarizer with OpenAI API")

    async def summarize(self, text: str, max_length: int = 200) -> str:
        """Summarize text using OpenAI.

        Args:
            text: Text to summarize
            max_length: Maximum length of summary in words

        Returns:
            Summarized text, or original truncated if API fails
        """
        if not text or len(text.strip()) == 0:
            return ""

        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": f"Summarize this in under {max_length} words, focusing on key points:\n\n{text}"
                    }
                ],
                temperature=0.7,
                max_tokens=max_length,
                timeout=10
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"Summarized {len(text)} chars to {len(summary)} chars")
            return summary

        except Exception as e:
            logger.warning(f"OpenAI summarization failed: {e}, using fallback")
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
