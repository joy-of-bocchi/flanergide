# storage/ — Persistence Layer

## Purpose

The `storage/` directory contains persistent data: Chroma vector database files and text files for short-term memory. This layer abstracts storage details from services.

---

## Directory Structure

```
storage/
├── CLAUDE.md           # This file
├── chroma_db/          # Chroma database files (gitignored)
│   ├── 0/
│   ├── 1/
│   └── ...
└── state/              # Short-term memory text files (gitignored)
    ├── current_mood.txt
    ├── recent_thoughts.txt
    └── blog_cache.json
```

---

## Chroma Database

### What is Chroma?

Chroma is an embedded vector database optimized for:
- **Semantic search** (embedding-based similarity)
- **Fast queries** (optimized indexing)
- **Embedded persistence** (no separate server)
- **Flexible metadata** (filter by type, timestamp, etc.)

### Persistence Model

**File Structure**:
```
chroma_db/
├── 0/                    # Partition 0
│   ├── data.db          # SQLite database
│   ├── index.pkl        # Index file
│   └── index.log        # Index metadata
├── 1/                    # Partition 1
│   └── ...
└── hnswlib_data/        # HNSW index (vector search)
    └── index.hnswlib
```

**Size Estimates**:
- Empty database: ~5 MB
- 10,000 events: ~50-100 MB
- 100,000 events: ~500 MB - 1 GB
- Depends on metadata size, embedding dimensions

### Initialization

**First Run**:
```python
from chromadb import Client

client = Client(persist_directory="./app/storage/chroma_db")
collection = client.get_or_create_collection("events")
# Automatically creates chroma_db/ directory structure
```

**Subsequent Runs**:
```python
client = Client(persist_directory="./app/storage/chroma_db")
# Automatically loads existing database
collection = client.get_collection("events")
```

### Backup and Recovery

**Backup** (copy entire directory):
```bash
cp -r app/storage/chroma_db app/storage/chroma_db.backup
```

**Restore**:
```bash
rm -rf app/storage/chroma_db
cp -r app/storage/chroma_db.backup app/storage/chroma_db
```

**Size Check**:
```bash
du -sh app/storage/chroma_db
```

---

## Text Files (State Directory)

### File Structure

#### current_mood.txt (JSON)
```json
{
  "mood": "focused",
  "updated_at": 1699888888,
  "context": "Working on backend features"
}
```

**Purpose**: Track your current emotional state
**Updated by**: `StateManager.update_mood()` or phone sync
**Read by**: Routes when responding with current state

#### recent_thoughts.txt (Plain Text)
```
Recent thoughts and blog summaries.

**Backend Design Patterns**
FastAPI is great for async APIs. StateFlow patterns are clean.

**Home Server Setup**
Running services at home gives you full control. Cloudflare Tunnel keeps it secure.
```

**Purpose**: Human-readable summary of recent thoughts
**Updated by**: Blog scraper + summarizer on schedule
**Read by**: Phone sync responses

#### blog_cache.json (JSON)
```json
[
  {
    "title": "Backend Design Patterns",
    "body": "Long full text...",
    "summary": "Short summary...",
    "url": "https://your-blog.com/backend-design",
    "published_at": 1699886666,
    "scraped_at": 1699888888
  }
]
```

**Purpose**: Structured blog post cache
**Updated by**: Blog scraper every N hours
**Read by**: `StateManager.get_recent_thoughts()`

### File Initialization

**First Run** (missing files):
```python
# StateManager creates defaults
state_manager = StateManager("./app/storage/state")
# If files don't exist, creates:
# - current_mood.txt: {"mood": "neutral", "updated_at": 0, "context": ""}
# - recent_thoughts.txt: "" (empty)
# - blog_cache.json: [] (empty array)
```

**Subsequent Runs**:
```python
# Loads existing files, preserves data
state = await state_manager.get_current_mood()
# Returns: {"mood": "focused", ...}
```

---

## Storage Reliability

### Atomic Writes

Use atomic file operations to prevent corruption:

```python
import json
import tempfile
import os

def atomic_write(filepath: str, data: dict):
    """Write JSON atomically using temp file"""
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=os.path.dirname(filepath),
        delete=False
    ) as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name

    # Atomic rename
    os.replace(tmp_path, filepath)
```

**Why**: If write is interrupted (power loss, crash), file isn't corrupted

### Permissions

Ensure files are readable/writable:

```python
import os

def ensure_readable(filepath: str):
    """Ensure file is readable/writable"""
    if os.path.exists(filepath):
        os.chmod(filepath, 0o644)  # rw- r-- r--

def ensure_dir_writable(dirpath: str):
    """Ensure directory is writable"""
    os.makedirs(dirpath, exist_ok=True)
    os.chmod(dirpath, 0o755)  # rwx r-x r-x
```

---

## Scaling Considerations

### When Chroma Gets Large

**Monitor Size**:
```bash
# Check directory size
du -sh app/storage/chroma_db

# Check file counts
find app/storage/chroma_db -type f | wc -l
```

**If > 1 GB**:
- Archive old events (move to backup)
- Implement retention policy (delete events > 1 year old)
- Consider distributed storage (cloud backup)

### Backup Strategy

**Daily Backup**:
```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
tar -czf backups/chroma_db_$TIMESTAMP.tar.gz app/storage/chroma_db
```

**Keep Last N Backups**:
```bash
# Keep last 30 days
find backups/ -name "chroma_db_*.tar.gz" -mtime +30 -delete
```

### Cloud Backup (Optional)

Upload to cloud for disaster recovery:
```bash
# AWS S3 example
aws s3 sync app/storage/ s3://my-backup-bucket/flanergide-storage/
```

---

## Git Ignore Configuration

**Add to .gitignore**:
```
# Chroma vector database (large, regenerable)
app/storage/chroma_db/

# State files (private, per-user)
app/storage/state/

# Backups
backups/
*.tar.gz
```

**Reason**: Database files are large, personal data shouldn't be in git

---

## Development vs. Production

### Development

```python
# Use in-memory for fast tests
client = Client()  # No persist_directory
collection = client.create_collection("test")

# Or use temporary directory
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    client = Client(persist_directory=tmpdir)
```

### Production (Home Server)

```python
# Persistent storage on disk
client = Client(persist_directory="/var/lib/flanergide/chroma_db")
state_manager = StateManager("/var/lib/flanergide/state")

# Ensure permissions
os.makedirs("/var/lib/flanergide", mode=0o755, exist_ok=True)
```

---

## Monitoring and Debugging

### Check Database Health

```python
# Count events
collection = client.get_collection("events")
count = collection.count()
print(f"Total events: {count}")

# Check metadata
results = collection.get(
    limit=5,
    include=["metadatas", "documents", "distances"]
)
for i, metadata in enumerate(results["metadatas"]):
    print(f"Event {i}: {metadata}")
```

### Inspect State Files

```bash
# Read mood
cat app/storage/state/current_mood.txt | jq .

# Read thoughts
head -20 app/storage/state/recent_thoughts.txt

# Check cache
cat app/storage/state/blog_cache.json | jq '.[0]'
```

---

## Data Cleanup

### Delete Old Events

```python
async def cleanup_old_events(days: int = 30):
    """Delete events older than N days"""
    cutoff_timestamp = int(time.time()) - (days * 86400)

    # Get all events
    results = collection.get()

    # Filter by timestamp
    for doc_id, metadata in zip(results["ids"], results["metadatas"]):
        if metadata.get("timestamp", 0) < cutoff_timestamp:
            collection.delete(ids=[doc_id])

# Schedule daily
# In background task:
await cleanup_old_events(days=365)  # Keep 1 year
```

### Export Data

```python
def export_events_json(output_file: str):
    """Export all events to JSON for backup"""
    results = collection.get(include=["documents", "metadatas"])

    with open(output_file, "w") as f:
        json.dump({
            "events": [
                {
                    "id": doc_id,
                    "document": doc,
                    "metadata": meta
                }
                for doc_id, doc, meta in zip(
                    results["ids"],
                    results["documents"],
                    results["metadatas"]
                )
            ]
        }, f, indent=2)
```

---

## Performance Tips

### Chroma Optimization

1. **Batch inserts**: Insert 100+ events at once (faster than one-by-one)
   ```python
   collection.add(documents=[...], metadatas=[...], ids=[...])
   ```

2. **Use appropriate collection**: One collection per data type
   ```python
   events = client.get_or_create_collection("events")
   messages = client.get_or_create_collection("messages")
   ```

3. **Limit query results**: Use `n_results` parameter
   ```python
   results = collection.query(query_texts=[...], n_results=10)
   ```

### Text File Optimization

1. **Don't read/write on every request**: Cache in memory
2. **Use JSON for structured data**: Easy to parse and validate
3. **Keep files < 10 MB**: Large files slow to read

---

## Troubleshooting

### Chroma Won't Start

**Error**: `Failed to get metadata of ... No such file or directory`

**Solution**:
```python
import os
os.makedirs("./app/storage/chroma_db", exist_ok=True)
# Try again
```

### State File Corrupted

**Error**: `json.JSONDecodeError`

**Solution**:
```python
# Restore from backup
import shutil
shutil.copy("app/storage/state/current_mood.txt.bak", "app/storage/state/current_mood.txt")

# Or reset to default
with open("app/storage/state/current_mood.txt", "w") as f:
    json.dump({"mood": "neutral", "updated_at": 0, "context": ""}, f)
```

### Out of Disk Space

**Solution**:
```bash
# Clean up old backups
rm -rf backups/chroma_db_*.tar.gz
# Or archive to cloud
aws s3 sync app/storage/chroma_db s3://my-bucket/archive/
```

---

## Notes for Implementation

- **Always check path exists** before reading files
- **Use atomic writes** for critical data
- **Implement backup strategy** early (before you have important data)
- **Monitor disk usage** (set up alerts)
- **Test recovery** (restore from backup and verify)
- **Version your schema** (if you change JSON structure)

---

See related files:
- `CLAUDE.md` — Backend overview
- `../services/CLAUDE.md` — Services that use storage
- `../api/routes/CLAUDE.md` — Routes that trigger storage operations
