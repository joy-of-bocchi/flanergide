# Summary System Documentation

## Overview

The Summary System provides AI-powered analysis of your daily and weekly activities based on:
1. **Phone text logs** - Captured text from apps on your Android device
2. **Blog posts** - Posts published on your personal blog

The system accumulates data in `.log` files and uses an LLM (via Ollama) to generate insightful summary across 4 analysis dimensions:
- **What you did** (activities, time allocation, productivity)
- **What was on your mind** (topics, themes, concerns)
- **Mood analysis** (emotional state, energy levels)
- **Personality insights** (behavioral patterns, communication style)

---

## Architecture

### Data Flow

```
Phone Logs Upload (POST /api/logs/upload)
    ↓
1. Store in ChromaDB (existing behavior)
2. Append to daily.log file (NEW)
    ↓
storage/analysis/YYYY-MM-DD/daily.log

When summary requested (GET /api/summary/*)
    ↓
1. Read accumulated log files
2. Filter blog posts by date
3. Generate LLM prompt with all data
4. Get analysis from Ollama
5. Save to summary.md
    ↓
storage/analysis/YYYY-MM-DD/summary.md
```

### File Structure

```
storage/analysis/
├── 2025-11-14/
│   ├── daily.log              # Accumulated phone logs
│   └── summary.md          # Generated analysis
├── 2025-11-15/
│   ├── daily.log
│   └── summary.md
└── 2025-11-09_to_2025-11-15/
    ├── weekly.log             # Combined logs from week
    └── summary.md          # Weekly analysis
```

### Daily Log Format

```
[HH:MM:SS] [app.package.name] Text content here
[14:23:15] [com.instagram.android] hey how are you doing
[15:30:42] [com.android.vscode] fixed the authentication bug
```

---

## API Endpoints

### 1. GET /api/summary/yesterday

Generate summary for yesterday.

**Authentication**: JWT Bearer token required

**Response**:
```json
{
  "summary": "# Daily Summary - 2025-11-14\n\n## What You Did Today...",
  "metadata": {
    "generated_at": "2025-11-15T10:30:00",
    "date_range": "2025-11-14",
    "log_count": 47,
    "blog_count": 1,
    "analysis_type": "daily"
  },
  "log_file_path": "./app/storage/analysis/2025-11-14/daily.log",
  "summary_file_path": "./app/storage/analysis/2025-11-14/summary.md"
}
```

**Example**:
```bash
curl -X GET "http://localhost:8000/api/summary/yesterday" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 2. GET /api/summary/today

Generate summary for today (in-progress).

**Authentication**: JWT Bearer token required

**Note**: Includes a disclaimer that data is incomplete.

**Example**:
```bash
curl -X GET "http://localhost:8000/api/summary/today" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 3. GET /api/summary/week

Generate weekly summary for last 7 days.

**Authentication**: JWT Bearer token required

**Query Parameters**:
- `start_date` (optional): Start date in YYYY-MM-DD format (defaults to 7 days ago)
- `end_date` (optional): End date in YYYY-MM-DD format (defaults to today)

**Example**:
```bash
# Last 7 days
curl -X GET "http://localhost:8000/api/summary/week" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Custom date range
curl -X GET "http://localhost:8000/api/summary/week?start_date=2025-11-01&end_date=2025-11-07" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 4. GET /api/summary/date/{date}

Generate summary for a specific date.

**Authentication**: JWT Bearer token required

**Path Parameters**:
- `date`: Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET "http://localhost:8000/api/summary/date/2025-11-10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Summary Output Format

All summary is returned as Markdown with structured sections:

```markdown
# Daily Summary - 2025-11-15

## What You Did Today
- Worked on backend API from 9am-2pm
- Researched ChromaDB architecture
- Built summary system
- Productivity: High focus on technical work

## What Was On Your Mind
- Vector database implementation details
- How to structure data for LLM analysis
- Career growth and skill development
- Recurring theme: System architecture design

## Mood Analysis
- Overall: Focused and engaged
- Morning: Energetic, productive coding session
- Afternoon: Contemplative, research-oriented
- Language patterns: Technical, detailed, systematic
- Energy level: Sustained throughout day

## Personality Insights
- Communication style: Direct, technical, example-driven
- Cognitive patterns: Detail-oriented, prefers understanding full architecture
- Work style: Deep focus sessions, minimal context switching
- Problem-solving: Research-first approach, builds mental models
- Values: Code quality, thorough understanding, efficient systems

---
Generated: 2025-11-15 23:45:00
Data sources: 47 text logs, 1 blog post
```

---

## Services & Components

### LogAccumulator

**File**: `app/services/log_accumulator.py`

**Purpose**: Accumulates text logs into daily `.log` files in real-time.

**Key Methods**:
- `append_text_log(text, app_package, timestamp, device_id)` - Append single log
- `get_log_content(date)` - Read full daily log
- `get_date_range_logs(start_date, end_date)` - Get logs for multiple days
- `create_weekly_log_file(start_date, end_date)` - Combine daily logs into weekly file

**Usage**:
```python
# Automatically called on each log upload
log_accumulator.append_text_log(
    text="hey how are you",
    app_package="com.instagram.android",
    timestamp=1699888888000,
    device_id="pixel-7-abc123"
)
```

---

### SummaryService

**File**: `app/services/summary_service.py`

**Purpose**: Generates LLM-based summary from accumulated data.

**Key Methods**:
- `generate_daily_summary(date)` - Daily analysis
- `generate_today_summary()` - In-progress day analysis
- `generate_weekly_summary(start_date, end_date)` - Weekly analysis

**Data Sources**:
1. Phone logs from `LogAccumulator`
2. Blog posts from `StateManager` (filtered by publication date)

**Process**:
1. Gather logs for date/range
2. Filter blog posts by publication date
3. Build combined data string
4. Generate LLM prompt (from `summary_prompts.py`)
5. Call Ollama for analysis
6. Save summary to markdown file

---

### Prompt Templates

**File**: `app/prompts/summary_prompts.py`

**Daily Analysis Prompt**: Analyzes one day across 4 dimensions
**Weekly Analysis Prompt**: Looks for patterns and trends over the week

**Key Features**:
- Structured markdown output
- Evidence-based analysis (must quote from data)
- Honest, non-judgmental tone
- Specific guidelines for each section

---

## Configuration

Add to your `.env` file:

```bash
# Required (existing)
JWT_SECRET=your_secret_key_here
CLOUDFLARE_TUNNEL_URL=https://your-tunnel.trycloudflare.com
BLOG_URL=https://your-blog.com

# Optional (new)
ANALYSIS_DIR=./app/storage/analysis  # Default value
```

---

## How Blog Posts Are Integrated

### Blog Scraper (Existing)
- Runs every 48 hours (configurable)
- Fetches posts from your blog URL (RSS or HTML)
- Stores in `state_manager` cache (`blog_cache.json`)

### Summary Integration (New)
- When generating summary, filters cached blog posts by **publication date**
- Only includes posts published within the analysis period
- Example: Daily summary for Nov 15 only includes posts published on Nov 15

**Blog Post Data**:
```json
{
  "title": "Building a Vector Database Backend",
  "body": "Full post content...",
  "url": "https://blog.com/vector-db",
  "published_at": 1699888888,
  "summary": "Short AI-generated summary..."
}
```

---

## Testing

### 1. Check Imports

```bash
cd backend
python test_imports.py
```

### 2. Start Server

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python -m app.main
```

### 3. Upload Test Logs

```bash
# First, get a JWT token
curl -X POST "http://localhost:8000/api/token/generate" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "test-device", "device_name": "Test Phone"}'

# Upload sample logs
curl -X POST "http://localhost:8000/api/logs/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {
        "text": "Working on the backend API",
        "appPackage": "com.android.vscode",
        "timestamp": 1699888888000
      }
    ]
  }'
```

### 4. Generate Summary

```bash
# Get today's summary
curl -X GET "http://localhost:8000/api/summary/today" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Check Generated Files

```bash
ls -la app/storage/analysis/2025-11-15/
# Should see: daily.log and summary.md
```

---

## LLM Requirements

### Ollama Setup

The summary system uses **Ollama** with the **Mistral** model.

**Installation**:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull Mistral model
ollama pull mistral

# Verify it's running
ollama list
```

**Model Configuration**:
- Default model: `mistral` (hardcoded in `summarizer.py`)
- Default host: `http://localhost:11434`
- Timeout: 300 seconds (5 minutes)

**Token Limits**:
- Daily summary: Up to 4000 tokens
- Weekly summary: Up to 4000 tokens

---

## Troubleshooting

### No summary generated

**Check**:
1. Is Ollama running? (`ollama list`)
2. Are there logs for that date? (`ls app/storage/analysis/YYYY-MM-DD/`)
3. Check server logs for LLM errors

### Empty daily.log file

**Check**:
1. Have you uploaded logs for that date?
2. Check `logs.py` route - is `log_accumulator.append_text_log()` being called?
3. Verify `analysis_dir` exists and is writable

### Blog posts not included

**Check**:
1. Is blog scraper enabled? (`ENABLE_BLOG_SCRAPER=true`)
2. Are posts in cache? (`cat app/storage/state/blog_cache.json`)
3. Do post publication dates match the analysis period?

### LLM timeout

**Increase timeout** in `summarizer.py`:
```python
response = await self.client.post(
    ...,
    timeout=600.0  # 10 minutes instead of 5
)
```

---

## Future Enhancements

**Potential improvements**:

1. **Scheduled Generation**: Auto-generate summary at end of each day
2. **Caching**: Store generated summary, return cached version if already generated
3. **Comparison Mode**: Compare this week vs last week
4. **Trend Analysis**: Track mood/productivity trends over months
5. **ChromaDB Storage**: Store summary in vector DB for semantic search
6. **Structured Output**: Parse LLM output into JSON fields
7. **Push Notifications**: Send daily summary to phone
8. **Custom Prompts**: Allow users to customize analysis angles
9. **Multi-language Support**: Analyze logs in different languages
10. **Privacy Controls**: Redact sensitive topics before LLM analysis

---

## Security Considerations

### Data Privacy

- **Local processing**: All LLM analysis runs locally via Ollama (no cloud API)
- **JWT authentication**: All endpoints require valid device token
- **No analytics**: No usage data sent to external services

### Best Practices

1. **Keep JWT secret secure**: Never commit to git
2. **Review generated summary**: May contain sensitive personal info
3. **Backup analysis directory**: Summary files are valuable over time
4. **Limit retention**: Consider auto-deleting old logs after N months

---

## API Documentation

Full interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Look for the **"summary"** tag for all summary endpoints.
