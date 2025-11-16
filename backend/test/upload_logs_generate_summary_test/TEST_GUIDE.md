# Summary System Test Guide

## Quick Test Steps

### Step 1: Get a JWT Token

You need a valid JWT token to test the endpoints. Since your server is running, you should already have a way to generate tokens. If you have an existing token, use that. Otherwise, check your authentication setup.

**If you don't have a token**, you can temporarily disable auth for testing or use an existing device token.

---

### Step 2: Upload Test Logs

I've created a test data file: `test_logs.json`

Run this command (replace `YOUR_TOKEN` with your actual JWT):

```bash
curl -X POST "http://localhost:8000/api/logs/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_logs.json
```

**Expected response:**
```json
{
  "uploaded": 8,
  "failed": 0,
  "status": "success",
  "message": "8 logs stored successfully"
}
```

---

### Step 3: Generate Today's Summary

```bash
curl -X GET "http://localhost:8000/api/summary/today" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**This will:**
1. Read all logs from today's `daily.log` file
2. Filter blog posts published today
3. Send everything to Ollama (Mistral model)
4. Generate AI summary with 4 analysis sections
5. Save to `summary.md`

**Expected response:**
```json
{
  "summary": "# Daily Summary - 2025-11-15\n\n## What You Did Today\n...",
  "metadata": {
    "generated_at": "2025-11-15T...",
    "date_range": "2025-11-15",
    "log_count": 8,
    "blog_count": 0,
    "analysis_type": "today"
  },
  "log_file_path": "./app/storage/analysis/2025-11-15/daily.log",
  "summary_file_path": "./app/storage/analysis/2025-11-15/summary.md"
}
```

**Note:** Generation may take 30-60 seconds depending on Ollama's speed.

---

### Step 4: Check Generated Files

After running the summary command, check these files:

```bash
# Today's directory (replace date with actual date)
ls -la backend/app/storage/analysis/2025-11-15/

# You should see:
# - daily.log          (accumulated phone logs)
# - summary.md      (AI-generated analysis)
```

**View the daily log:**
```bash
cat backend/app/storage/analysis/2025-11-15/daily.log
```

Expected format:
```
[HH:MM:SS] [com.android.vscode] Working on the summary system...
[HH:MM:SS] [com.brave.browser] Researching how to integrate ChromaDB...
```

**View the summary:**
```bash
cat backend/app/storage/analysis/2025-11-15/summary.md
```

Expected format:
```markdown
# Daily Summary - 2025-11-15

## What You Did Today
- Worked on backend API implementation
- Researched vector databases
- Social messaging on Instagram

## What Was On Your Mind
- Summary system architecture
- ChromaDB integration patterns
...
```

---

## Alternative: Use the Test Script (If Dependencies Available)

If you have `httpx` installed in your venv, you can run:

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python test_summary_endpoints.py
```

This will automatically:
1. Generate a JWT token
2. Upload test logs
3. Generate summary
4. Show results

---

## Testing Other Endpoints

### Get Yesterday's Summary
```bash
curl -X GET "http://localhost:8000/api/summary/yesterday" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Weekly Summary (Last 7 Days)
```bash
curl -X GET "http://localhost:8000/api/summary/week" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Custom Date Range
```bash
curl -X GET "http://localhost:8000/api/summary/week?start_date=2025-11-01&end_date=2025-11-07" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Specific Date Summary
```bash
curl -X GET "http://localhost:8000/api/summary/date/2025-11-10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Troubleshooting

### No logs found
- Make sure you uploaded logs for the date you're querying
- Check `backend/app/storage/analysis/YYYY-MM-DD/daily.log` exists

### Ollama timeout
- Make sure Ollama is running: `ollama list`
- Check Ollama can respond: `ollama run mistral "Hello"`
- Increase timeout in `summarizer.py` if needed

### Empty summary
- Check server logs for LLM errors
- Verify Ollama is working correctly
- Make sure you have data for the requested date

### JWT errors
- Verify your token hasn't expired
- Check JWT_SECRET in your `.env` matches
- Generate a new token if needed

---

## What to Verify

After successful test:

- [ ] `daily.log` file created with your test logs
- [ ] `summary.md` file created with AI analysis
- [ ] Summary has 4 sections (activities, thoughts, mood, personality)
- [ ] API response includes correct metadata (log count, date, etc.)
- [ ] No errors in server logs

---

## Next Steps

Once testing is successful:

1. **Integrate with your Android app** - Have it upload logs regularly
2. **Set up scheduled summary** - Add cron job to generate daily summaries
3. **Add blog scraping** - Ensure blog posts are being cached
4. **Test with real data** - Use actual phone logs over several days
5. **Customize prompts** - Adjust analysis angles in `summary_prompts.py`

---

## Files Reference

- **Test data**: `test_logs.json` (sample phone logs)
- **Test script**: `test_summary_endpoints.py` (automated testing)
- **Storage**: `app/storage/analysis/` (all generated files)
- **Documentation**: `COMMENTARY_SYSTEM.md` (full system docs)
