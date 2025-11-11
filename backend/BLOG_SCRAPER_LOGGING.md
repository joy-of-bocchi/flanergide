# Blog Scraper Logging Guide

## Overview

Comprehensive logging has been added to the blog scraper and state manager to help you debug and monitor what's happening during blog scraping operations.

---

## What Was Added

### 1. BlogScraper Logging (`app/services/blog_scraper.py`)

#### Initialization
```
BlogScraper initialized for URL: https://your-blog.com
```

#### RSS Feed Fetching
```
INFO: Attempting to fetch RSS from 4 possible URLs
DEBUG: Trying RSS feed at: https://your-blog.com/feed.xml
✓ RSS feed found at https://your-blog.com/feed.xml with 15 entries
Successfully parsed 10 posts from RSS
```

**Or if no RSS found:**
```
WARNING: No RSS feeds found at any of the 4 attempted URLs
```

#### HTML Scraping (Fallback)
```
INFO: Attempting HTML scrape from https://your-blog.com
✓ Successfully fetched HTML (45231 bytes)
Found 12 article containers in HTML
DEBUG:   Article 1: 'My First Post' from https://your-blog.com/post-1
DEBUG:   Article 2: 'Second Post Title' from https://your-blog.com/post-2
Successfully parsed 12 posts from HTML
```

#### Error Handling
```
ERROR: HTML parsing failed: ConnectError - Connection refused
ERROR: RSS parsing failed with critical error: TimeoutError - Request timed out
```

---

### 2. StateManager Blog Cache Logging (`app/services/state_manager.py`)

#### Cache Update Started
```
[BlogCache] Starting update with 10 posts
```

#### Summarization (if enabled)
```
[BlogCache] Summarizing 10 posts using AI...
[BlogCache] ✓ Summarization complete
```

#### File Writing
```
[BlogCache] Writing 10 posts to ./app/storage/state/blog_cache.json
[BlogCache] ✓ Cache file written
```

#### Individual Posts
```
[BlogCache]   Post 1: Building APIs with FastAPI
[BlogCache]   Post 2: Docker Tips and Tricks
[BlogCache]   Post 3: Python Performance Tuning
```

#### Completion
```
[BlogCache] ✓ Successfully updated blog cache with 10 posts
```

#### Error Handling
```
[BlogCache] ✗ Failed to update blog cache: FileNotFoundError - [Errno 2] No such file or directory
```

---

## How to Enable Debug Logging

To see **ALL** debug messages (very verbose), change the log level in `.env`:

```
LOG_LEVEL=DEBUG
```

The default is `INFO`, which shows:
- ✓ Initialization
- ✓ Success messages
- ✓ Summary statistics
- ✗ Errors and warnings

Debug messages include:
- Individual RSS URL attempts
- Each post parsed
- Detailed file operations
- Connection details

---

## Example Full Log Output

### Successful Run
```
2025-11-11 15:28:01 | INFO     | app.services.blog_scraper | BlogScraper initialized for URL: https://example.com
2025-11-11 15:28:01 | INFO     | app.main | Blog scraper configured for https://example.com
2025-11-11 15:28:02 | INFO     | app.services.blog_scraper | Starting blog scrape from https://example.com
2025-11-11 15:28:02 | INFO     | app.services.blog_scraper | Attempting to fetch RSS from 4 possible URLs
2025-11-11 15:28:03 | DEBUG    | app.services.blog_scraper | Trying RSS feed at: https://example.com/feed.xml
2025-11-11 15:28:04 | INFO     | app.services.blog_scraper | ✓ RSS feed found at https://example.com/feed.xml with 20 entries
2025-11-11 15:28:04 | INFO     | app.services.blog_scraper | Successfully parsed 10 posts from RSS
2025-11-11 15:28:04 | INFO     | app.services.blog_scraper | Fetched 10 posts from RSS
2025-11-11 15:28:04 | INFO     | app.services.state_manager | [BlogCache] Starting update with 10 posts
2025-11-11 15:28:04 | INFO     | app.services.state_manager | [BlogCache] Summarizing 10 posts using AI...
2025-11-11 15:28:45 | INFO     | app.services.state_manager | [BlogCache] ✓ Summarization complete
2025-11-11 15:28:45 | INFO     | app.services.state_manager | [BlogCache] ✓ Cache file written
2025-11-11 15:28:45 | DEBUG    | app.services.state_manager | [BlogCache]   Post 1: Building FastAPI Applications
2025-11-11 15:28:45 | DEBUG    | app.services.state_manager | [BlogCache]   Post 2: Docker Best Practices
2025-11-11 15:28:45 | DEBUG    | app.services.state_manager | [BlogCache]   Post 3: Python Tips and Tricks
2025-11-11 15:28:45 | INFO     | app.services.state_manager | [BlogCache] ✓ Successfully updated blog cache with 10 posts
```

### Fallback to HTML
```
2025-11-11 15:28:02 | INFO     | app.services.blog_scraper | Starting blog scrape from https://example.com
2025-11-11 15:28:02 | INFO     | app.services.blog_scraper | Attempting to fetch RSS from 4 possible URLs
2025-11-11 15:28:02 | DEBUG    | app.services.blog_scraper | Trying RSS feed at: https://example.com/feed.xml
2025-11-11 15:28:03 | DEBUG    | app.services.blog_scraper | RSS feed at https://example.com/feed.xml not available: HTTPStatusError - 404 Client Error: Not Found
2025-11-11 15:28:03 | DEBUG    | app.services.blog_scraper | Trying RSS feed at: https://example.com/feed.json
2025-11-11 15:28:03 | DEBUG    | app.services.blog_scraper | RSS feed at https://example.com/feed.json not available: HTTPStatusError - 404 Client Error: Not Found
2025-11-11 15:28:03 | DEBUG    | app.services.blog_scraper | Trying RSS feed at: https://example.com/rss
2025-11-11 15:28:03 | DEBUG    | app.services.blog_scraper | RSS feed at https://example.com/rss not available: HTTPStatusError - 404 Client Error: Not Found
2025-11-11 15:28:03 | DEBUG    | app.services.blog_scraper | Trying RSS feed at: https://example.com/feed
2025-11-11 15:28:03 | DEBUG    | app.services.blog_scraper | RSS feed at https://example.com/feed not available: HTTPStatusError - 404 Client Error: Not Found
2025-11-11 15:28:03 | WARNING  | app.services.blog_scraper | No RSS feeds found at any of the 4 attempted URLs
2025-11-11 15:28:03 | INFO     | app.services.blog_scraper | Fetched 0 posts from RSS
2025-11-11 15:28:03 | INFO     | app.services.blog_scraper | RSS not available, falling back to HTML scraping
2025-11-11 15:28:04 | INFO     | app.services.blog_scraper | Attempting HTML scrape from https://example.com
2025-11-11 15:28:04 | INFO     | app.services.blog_scraper | ✓ Successfully fetched HTML (23456 bytes)
2025-11-11 15:28:04 | INFO     | app.services.blog_scraper | Found 8 article containers in HTML
2025-11-11 15:28:04 | DEBUG    | app.services.blog_scraper |   Article 1: 'My First Blog Post' from https://example.com/post-1
2025-11-11 15:28:04 | DEBUG    | app.services.blog_scraper |   Article 2: 'Second Post' from https://example.com/post-2
2025-11-11 15:28:04 | INFO     | app.services.blog_scraper | Successfully parsed 8 posts from HTML
2025-11-11 15:28:04 | INFO     | app.services.blog_scraper | Fetched 8 posts from HTML
```

### Error Case
```
2025-11-11 15:28:02 | INFO     | app.services.blog_scraper | Starting blog scrape from https://invalid-url.com
2025-11-11 15:28:02 | INFO     | app.services.blog_scraper | Attempting to fetch RSS from 4 possible URLs
2025-11-11 15:28:07 | DEBUG    | app.services.blog_scraper | Trying RSS feed at: https://invalid-url.com/feed.xml
2025-11-11 15:28:12 | DEBUG    | app.services.blog_scraper | RSS feed at https://invalid-url.com/feed.xml not available: ConnectError - Failed to resolve hostname
2025-11-11 15:28:12 | DEBUG    | app.services.blog_scraper | Trying RSS feed at: https://invalid-url.com/feed.json
2025-11-11 15:28:17 | DEBUG    | app.services.blog_scraper | RSS feed at https://invalid-url.com/feed.json not available: ConnectError - Failed to resolve hostname
2025-11-11 15:28:17 | WARNING  | app.services.blog_scraper | No RSS feeds found at any of the 4 attempted URLs
2025-11-11 15:28:17 | INFO     | app.services.blog_scraper | Attempting HTML scrape from https://invalid-url.com
2025-11-11 15:28:22 | ERROR    | app.services.blog_scraper | HTML parsing failed: ConnectError - Failed to resolve hostname
```

---

## Key Metrics You Can Monitor

### 1. **Is the scraper running?**
Look for: `Starting blog scrape from` + `Fetched X posts`

### 2. **Which method is working?**
- **RSS**: `✓ RSS feed found at ... with X entries`
- **HTML**: `Attempting HTML scrape` → `Found X article containers`

### 3. **Are summaries being generated?**
Look for: `[BlogCache] Summarizing X posts using AI...` + `✓ Summarization complete`

### 4. **Are files being written?**
Look for: `[BlogCache] ✓ Cache file written`

### 5. **How many posts are cached?**
Look for: `Successfully updated blog cache with X posts`

### 6. **Are there errors?**
Look for: `✗ Failed`, `ERROR`, `WARNING`

---

## Troubleshooting with Logs

### "No posts are being scraped"
1. Check: `Starting blog scrape from` message appears
2. Check: Did it try RSS or fall back to HTML?
3. If RSS: Is the RSS feed URL correct? Check the attempted URLs
4. If HTML: Are there article containers? Check `Found X article containers`

### "Blog scraper runs but nothing is cached"
1. Check: `[BlogCache] Starting update with` message
2. Check: Did summarization run? Look for `Summarizing` message
3. Check: Did file write succeed? Look for `Cache file written`
4. If error: Look for `✗ Failed` message with error details

### "Summarization is very slow"
1. This is normal - first summarization takes 30-60 seconds (model loading)
2. Subsequent summaries take 5-15 seconds
3. Check log timestamps to see duration

### "Blog scraper crashes"
1. Look for `ERROR` with full stack trace
2. Check if Ollama is running (if summarization is enabled)
3. Check if BLOG_URL in `.env` is valid and accessible

---

## Log Levels Explained

| Level | When Used | Examples |
|-------|-----------|----------|
| DEBUG | Detailed tracing | Individual URL attempts, post details |
| INFO | Normal operation | Initialization, counts, success |
| WARNING | Something unexpected | No RSS feeds found, fallback triggered |
| ERROR | Something failed | Connection error, summarization failed |

---

## How to View Logs

### 1. **While Server is Running**
Look at the terminal where you ran:
```powershell
python -m uvicorn app.main:app --reload
```

### 2. **Change Log Level**
Edit `.env`:
```
LOG_LEVEL=DEBUG      # Maximum verbosity (very detailed)
LOG_LEVEL=INFO       # Normal (default)
LOG_LEVEL=WARNING    # Only warnings and errors
LOG_LEVEL=ERROR      # Only errors
```

### 3. **Example Commands**

Start server with debug logging:
```powershell
$env:LOG_LEVEL="DEBUG"; python -m uvicorn app.main:app --reload
```

---

## Summary

The blog scraper now provides **clear, actionable logging** at every step:

✅ Initialization
✅ Feed discovery (RSS attempts)
✅ Post parsing (count and details)
✅ Summarization progress
✅ File operations
✅ Error reporting with context

**You can now easily see what's happening at each stage of the scraping and caching process!** 🔍

