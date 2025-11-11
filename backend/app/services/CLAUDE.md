# services/ — Business Logic Layer

## Purpose

Services contain all business logic and data manipulation. They are stateless, testable, and called by routes. Each service has a single responsibility.

---

## Directory Structure

```
services/
├── CLAUDE.md            # This file
├── vector_store.py      # Chroma vector DB operations
├── blog_scraper.py      # Blog content fetching and parsing
├── summarizer.py        # AI-powered text summarization
└── state_manager.py     # Short-term memory (text files)
```

---

## vector_store.py — Vector Database Service

Manages long-term memory using Chroma for semantic search.

### Core Operations

#### `insert(event: dict, device_id: str) -> str`

Store a new event with automatic embedding.

**Input**:
```python
event = {
    "type": "app_launch",
    "data": {"app": "instagram", "duration": 1200},
    "timestamp": 1699888888
}
device_id = "device-001"
```

**Process**:
1. Validate event schema
2. Generate text representation: `"App launch: instagram (duration: 1200s)"`
3. Chroma auto-embeds text using default model
4. Store in Chroma with metadata
5. Return event ID

**Output**:
```python
"event-abc123def456"
```

#### `search(query: str, limit: int = 10, filters: dict = None) -> list`

Semantic search over stored events.

**Input**:
```python
query = "when did I use Instagram"
filters = {"type": "app_launch"}
```

**Process**:
1. Embed query text
2. Search Chroma with cosine similarity
3. Apply filters if provided
4. Sort by similarity score
5. Return top-K results with scores

**Output**:
```python
[
    {
        "id": "event-abc123",
        "type": "app_launch",
        "data": {"app": "instagram"},
        "timestamp": 1699888888,
        "similarity_score": 0.92
    }
]
```

#### `recent(limit: int = 20, offset: int = 0, type_filter: str = None) -> list`

Get recent events without semantic search.

**Input**:
```python
limit = 20
offset = 0
type_filter = "app_launch"
```

**Process**:
1. Query Chroma for all documents
2. Sort by timestamp (newest first)
3. Apply type filter if provided
4. Paginate with limit/offset
5. Return results with metadata

**Output**:
```python
[
    {
        "id": "event-abc123",
        "type": "app_launch",
        "timestamp": 1699888888,
        "data": {...}
    }
]
```

#### `delete(event_id: str) -> bool`

Remove an event from Chroma.

**Input**:
```python
event_id = "event-abc123"
```

**Process**:
1. Verify event exists
2. Delete from Chroma
3. Return success

**Output**:
```python
True  # or raise exception if not found
```

### Implementation Pattern

```python
from chromadb import Client
import json

class VectorStore:
    def __init__(self, persist_dir: str):
        self.client = Client(persist_directory=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="events",
            metadata={"hnsw:space": "cosine"}
        )

    async def insert(self, event: dict, device_id: str) -> str:
        # Validate event
        if "type" not in event:
            raise ValueError("Event must have 'type'")

        # Generate text representation
        text = self._event_to_text(event)

        # Prepare metadata
        metadata = {
            "type": event.get("type"),
            "device_id": device_id,
            "timestamp": event.get("timestamp", int(time.time()))
        }

        # Insert into Chroma
        event_id = self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )

        return event_id[0]

    async def search(self, query: str, limit: int = 10, filters: dict = None) -> list:
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=filters
        )

        # Format results
        output = []
        for i, doc_id in enumerate(results["ids"][0]):
            output.append({
                "id": doc_id,
                "distance": results["distances"][0][i],
                "similarity_score": 1 - results["distances"][0][i],
                "metadata": results["metadatas"][0][i]
            })

        return output

    def _event_to_text(self, event: dict) -> str:
        """Convert event to human-readable text for embedding"""
        type_ = event.get("type", "unknown")
        data = event.get("data", {})

        if type_ == "app_launch":
            return f"App launch: {data.get('app')} (duration: {data.get('duration')}s)"
        elif type_ == "notification":
            return f"Notification from {data.get('source')}: {data.get('subject')}"
        else:
            return f"{type_}: {json.dumps(data)}"
```

---

## blog_scraper.py — Blog Content Service

Fetches and parses blog posts, updates cache.

### Core Operations

#### `fetch_and_parse() -> list`

Scrape blog homepage, extract posts.

**Process**:
1. Fetch HTML from `BLOG_URL`
2. Parse with BeautifulSoup
3. Extract post links and titles
4. Fetch each post, extract body text
5. Return structured posts

**Output**:
```python
[
    {
        "title": "Backend Design Patterns",
        "body": "Long text content...",
        "url": "https://your-blog.com/backend-design",
        "published_at": 1699886666,
        "scraped_at": 1699888888
    }
]
```

#### `parse_html(html: str) -> list`

Extract post metadata from HTML.

**Process**:
1. Find post containers (article, div.post, etc.)
2. Extract title, URL, date
3. Filter out non-content (nav, footer, etc.)
4. Return cleaned metadata

#### Implementation Pattern

```python
import httpx
from bs4 import BeautifulSoup
import feedparser

class BlogScraper:
    def __init__(self, blog_url: str):
        self.blog_url = blog_url

    async def fetch_and_parse(self) -> list:
        """Scrape blog and return structured posts"""
        # Try RSS first (cleaner)
        posts = await self._fetch_rss()
        if posts:
            return posts

        # Fallback to HTML scraping
        posts = await self._fetch_html()
        return posts

    async def _fetch_rss(self) -> list:
        """Try to parse RSS feed"""
        try:
            feed = feedparser.parse(self.blog_url + "/feed.xml")
            posts = []
            for entry in feed.entries[:10]:  # Last 10 posts
                posts.append({
                    "title": entry.title,
                    "body": entry.get("summary", ""),
                    "url": entry.link,
                    "published_at": self._parse_date(entry.published),
                    "scraped_at": int(time.time())
                })
            return posts
        except:
            return []

    async def _fetch_html(self) -> list:
        """Parse HTML if no RSS available"""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(self.blog_url)
            soup = BeautifulSoup(response.text, "html.parser")

            posts = []
            # Find post containers (adjust selectors for your blog)
            for article in soup.find_all("article"):
                title_elem = article.find("h2") or article.find("h3")
                link_elem = article.find("a")

                if title_elem and link_elem:
                    posts.append({
                        "title": title_elem.get_text().strip(),
                        "url": link_elem.get("href"),
                        "body": article.get_text()[:500],  # Preview
                        "published_at": int(time.time()),
                        "scraped_at": int(time.time())
                    })

            return posts

    def _parse_date(self, date_str: str) -> int:
        """Convert string date to Unix timestamp"""
        from dateutil import parser
        dt = parser.parse(date_str)
        return int(dt.timestamp())
```

---

## summarizer.py — Text Summarization Service

AI-powered summarization of blog posts and context.

### Core Operations

#### `summarize(text: str, max_length: int = 200) -> str`

Summarize long text using AI.

**Input**:
```python
text = "Very long blog post content..."
max_length = 200
```

**Process**:
1. Call OpenAI API (or local LLM)
2. Request summary under max_length
3. Return summarized text
4. Handle errors gracefully

**Output**:
```python
"Summary of key points in 150-200 characters"
```

#### Implementation Pattern

```python
import openai

class Summarizer:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    async def summarize(self, text: str, max_length: int = 200) -> str:
        """Summarize text using OpenAI"""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": f"Summarize this in under {max_length} words:\n\n{text}"
                    }
                ],
                temperature=0.7,
                max_tokens=max_length
            )
            return response.choices[0].message.content
        except Exception as e:
            # Fallback: return first N characters
            return text[:max_length]

    async def summarize_blog_posts(self, posts: list) -> list:
        """Summarize multiple blog posts"""
        summarized = []
        for post in posts:
            summary = await self.summarize(post["body"], max_length=200)
            summarized.append({
                **post,
                "summary": summary
            })
        return summarized
```

---

## state_manager.py — Short-Term Memory Service

Manages text files for mood, thoughts, blog summaries.

### Core Operations

#### `get_current_mood() -> dict`

Read current mood from file.

**Output**:
```python
{
    "mood": "focused",
    "updated_at": 1699888888,
    "context": "Working on backend features"
}
```

#### `update_mood(mood: str, context: str = None) -> dict`

Write new mood to file.

**Input**:
```python
mood = "tired"
context = "Long day of meetings"
```

**Process**:
1. Validate mood from predefined list
2. Update `current_mood.txt`
3. Record timestamp
4. Return confirmation

#### `get_recent_thoughts() -> dict`

Read recent thoughts/blog summaries.

**Output**:
```python
{
    "thoughts": "Latest blog post summary...",
    "blog_posts": [
        {"title": "...", "summary": "...", "url": "..."}
    ],
    "updated_at": 1699888888
}
```

#### `update_blog_cache(posts: list) -> bool`

Update blog post cache from scraper.

**Process**:
1. Summarize each post
2. Cache in `blog_cache.json`
3. Update `recent_thoughts.txt` with summaries
4. Record update timestamp

#### Implementation Pattern

```python
import json
import os
from typing import Optional

class StateManager:
    def __init__(self, state_dir: str):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.mood_file = os.path.join(state_dir, "current_mood.txt")
        self.thoughts_file = os.path.join(state_dir, "recent_thoughts.txt")
        self.blog_cache_file = os.path.join(state_dir, "blog_cache.json")
        self.valid_moods = ["happy", "sad", "focused", "tired", "anxious", "neutral"]

    async def get_current_mood(self) -> dict:
        """Read mood from file"""
        if not os.path.exists(self.mood_file):
            return {"mood": "neutral", "updated_at": 0, "context": ""}

        with open(self.mood_file, "r") as f:
            data = json.load(f)
        return data

    async def update_mood(self, mood: str, context: str = None) -> dict:
        """Write mood to file"""
        if mood not in self.valid_moods:
            raise ValueError(f"Invalid mood: {mood}")

        data = {
            "mood": mood,
            "updated_at": int(time.time()),
            "context": context or ""
        }

        with open(self.mood_file, "w") as f:
            json.dump(data, f, indent=2)

        return data

    async def get_recent_thoughts(self) -> dict:
        """Read thoughts and blog summaries"""
        thoughts = ""
        if os.path.exists(self.thoughts_file):
            with open(self.thoughts_file, "r") as f:
                thoughts = f.read()

        blog_posts = []
        if os.path.exists(self.blog_cache_file):
            with open(self.blog_cache_file, "r") as f:
                blog_posts = json.load(f)

        return {
            "thoughts": thoughts,
            "blog_posts": blog_posts,
            "updated_at": int(os.path.getmtime(self.thoughts_file)) if os.path.exists(self.thoughts_file) else 0
        }

    async def update_blog_cache(self, posts: list, summarizer=None) -> bool:
        """Update blog post cache"""
        # Summarize posts if summarizer provided
        if summarizer:
            for post in posts:
                if "summary" not in post:
                    post["summary"] = await summarizer.summarize(post["body"])

        # Cache all posts
        with open(self.blog_cache_file, "w") as f:
            json.dump(posts, f, indent=2)

        # Update thoughts file with latest summaries
        summaries = "\n\n".join([
            f"**{post['title']}**\n{post.get('summary', post.get('body', '')[:200])}"
            for post in posts[:5]  # Last 5 posts
        ])

        with open(self.thoughts_file, "w") as f:
            f.write(summaries)

        return True
```

---

## Service Design Rules

### ✅ DO

- Keep services **stateless** (no instance variables except config)
- Use **async/await** for all I/O
- **Validate input** before processing
- **Handle errors** gracefully (return defaults, not crash)
- **Log important operations** (but not sensitive data)
- **Write unit tests** for each service

### ❌ DON'T

- Store mutable state in service instances
- Use blocking I/O (requests, open files without async)
- Return raw database objects
- Catch all exceptions without logging
- Mix concerns (e.g., StateManager shouldn't call API)

---

## Error Handling Strategy

**For recoverable errors** (network, parse failure):
```python
try:
    posts = await scraper.fetch_and_parse()
except Exception as e:
    logger.error(f"Failed to scrape blog: {e}")
    posts = []  # Return empty list, not crash
```

**For validation errors** (bad input):
```python
if mood not in self.valid_moods:
    raise ValueError(f"Invalid mood: {mood}")  # Let caller handle
```

**For critical errors** (database corruption):
```python
except ChromaError as e:
    logger.critical(f"Vector DB corrupted: {e}")
    # Consider alerting admin or falling back gracefully
```

---

## Testing Services

Each service should be independently testable:

```python
# test_vector_store.py
import pytest

@pytest.mark.asyncio
async def test_insert_event():
    vs = VectorStore(":memory:")
    event_id = await vs.insert({"type": "test"}, device_id="test")
    assert event_id is not None

@pytest.mark.asyncio
async def test_search():
    vs = VectorStore(":memory:")
    await vs.insert({"type": "app_launch", "data": {"app": "instagram"}}, device_id="test")
    results = await vs.search("instagram", limit=10)
    assert len(results) > 0

# test_state_manager.py
@pytest.mark.asyncio
async def test_update_mood(tmp_path):
    sm = StateManager(str(tmp_path))
    result = await sm.update_mood("happy", context="Good day")
    assert result["mood"] == "happy"
```

---

See related files:
- `CLAUDE.md` — Backend overview
- `../api/routes/CLAUDE.md` — How routes call services
- `../models/CLAUDE.md` — Service input/output schemas
