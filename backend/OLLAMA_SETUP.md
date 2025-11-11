# Ollama Setup Guide

This guide walks you through setting up Ollama for the Flanergide backend.

## ⚙️ System Requirements

You have the following specs:
- **OS**: Windows 10 Home
- **RAM**: 16 GB (Excellent! ✓)
- **Free Disk**: ~78 GB (Plenty! ✓)
- **GPU**: Intel Iris Xe Graphics (Will help slightly)

**Recommended Model**: Mistral 7B (Perfect fit for your hardware)

---

## 📥 Step 1: Install Ollama

### Windows

1. Download Ollama from https://ollama.ai
2. Run the installer and follow the prompts
3. Restart your computer
4. Verify installation by opening Command Prompt and running:
   ```bash
   ollama --version
   ```

---

## 📦 Step 2: Download Mistral Model

Open a **new Command Prompt** and run:

```bash
ollama pull mistral
```

**What to expect:**
- First pull takes 5-10 minutes (downloads ~4.1 GB)
- Subsequent runs are instant (cached)
- You'll see progress: `pulling abcd1234... done`

**Output**:
```
pulling abcd1234...
pulling ef567890... done
digest: sha256:xxxxxxxxxxxxxxxxxxxx
total size: 4.1 GB
```

---

## 🚀 Step 3: Start Ollama Server

In a **dedicated Command Prompt** (keep it open), run:

```bash
ollama serve
```

**Expected output**:
```
2024-11-11 12:34:56.789 INFO Ollama server is listening at 127.0.0.1:11434
```

**Important**: Keep this terminal open! The server must be running for summarization to work.

---

## ✅ Step 4: Test Ollama (Optional but Recommended)

In a **new Command Prompt**, test that Ollama is working:

```bash
curl http://localhost:11434/api/generate -d "{\"model\": \"mistral\", \"prompt\": \"Hello, what is 2+2?\"}" -X POST
```

**Expected response** (may take 10-30 seconds):
```json
{
  "model": "mistral",
  "response": " 2+2 equals 4. This is a basic...",
  "done": true
}
```

---

## 🔄 Step 5: Update Backend Configuration

### Option A: Using Defaults (Recommended)

If Ollama is running on `http://localhost:11434`, no action needed! The backend defaults to this address.

Your `.env` file should have:
```
OLLAMA_HOST=http://localhost:11434
```

### Option B: Custom Ollama Host

If Ollama is running on a different machine or port, update `.env`:

```
# Example: Ollama on different machine
OLLAMA_HOST=http://192.168.1.100:11434

# Example: Ollama on different port
OLLAMA_HOST=http://localhost:8000
```

---

## 🧪 Step 6: Test Backend Integration

### Terminal 1: Keep Ollama Server Running
```bash
ollama serve
```

### Terminal 2: Install Dependencies
```bash
cd backend/
pip install -r requirements.txt
```

### Terminal 3: Run Test Script
```bash
cd backend/
python test_ollama.py
```

**Expected output**:
```
================================================================================
Testing Ollama Integration
================================================================================

✓ Summarizer initialized successfully

────────────────────────────────────────────────────────────────────────────────
Sample Text:
────────────────────────────────────────────────────────────────────────────────
Artificial intelligence (AI) is transforming...

────────────────────────────────────────────────────────────────────────────────
Summarizing (this may take 30-60 seconds with Mistral)...
────────────────────────────────────────────────────────────────────────────────

✓ Summary generated successfully!

Summary (45 words):
AI is revolutionizing various industries through machine learning and deep
learning, processing unstructured data efficiently. While these technologies
offer significant benefits in healthcare, finance, and education, they raise
ethical concerns about privacy and bias that society must address.

================================================================================
✓ All tests passed!
================================================================================
```

**Performance expectations**:
- First summarization: 30-60 seconds (model loading)
- Subsequent summaries: 5-15 seconds (cached model)

---

## 🚀 Step 7: Run Backend Server

### Terminal 2 or 3: Start Backend
```bash
cd backend/
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Initializing services...
INFO:     Summarizer initialized with Ollama at http://localhost:11434
```

---

## 🐛 Troubleshooting

### Error: "Connection refused at 127.0.0.1:11434"

**Solution**: Make sure Ollama server is running
```bash
ollama serve
```

### Error: "Model 'mistral' not found"

**Solution**: Download the model
```bash
ollama pull mistral
```

### Error: "Empty response from Ollama"

**Solution**: Wait 1-2 minutes for model to fully load on first use, then retry

### Model is very slow (>2 minutes per summarization)

**Possible causes**:
- Model still loading from disk (first use takes longest)
- Your system is low on free RAM
- Anti-virus is slowing down disk access

**Solutions**:
1. Check Task Manager for free RAM (should be >4 GB available)
2. Close unnecessary applications
3. If still slow, try `neural-chat` model (smaller, faster):
   ```bash
   ollama pull neural-chat
   ```
   Then update `app/services/summarizer.py` line 20: `self.model = "neural-chat"`

### Ollama crashes or disconnects

**Solution**: Restart Ollama server
```bash
# Stop the running server (Ctrl+C in the terminal)
ollama serve
```

---

## 📊 Performance Characteristics

### Mistral 7B (Recommended)

| Metric | Value |
|--------|-------|
| Model Size | 4.1 GB |
| RAM Usage | 8-10 GB |
| First Load | 30-60 seconds |
| Subsequent Requests | 5-15 seconds |
| Quality | Excellent ⭐⭐⭐⭐⭐ |

### Neural-Chat 7B (If Mistral is Slow)

| Metric | Value |
|--------|-------|
| Model Size | 4.1 GB |
| RAM Usage | 7-9 GB |
| First Load | 20-40 seconds |
| Subsequent Requests | 3-10 seconds |
| Quality | Good ⭐⭐⭐⭐ |

---

## 🔒 Security Notes

- **Offline Processing**: All data stays on your machine (no cloud calls)
- **Privacy**: Unlike OpenAI, Ollama never sends data to external servers
- **Storage**: Models are cached locally in `~/.ollama/models`

---

## 📝 What Changed from OpenAI

### Before (OpenAI)
```python
# Required: OpenAI API key
OPENAI_API_KEY=sk-xxx-xxx-xxx

# Cost: $0.002 per 1K tokens (~$1-5/month)
# Privacy: Data sent to OpenAI servers
# Latency: 1-3 seconds (network dependent)
```

### After (Ollama)
```python
# No API key needed!
OLLAMA_HOST=http://localhost:11434

# Cost: $0 (free)
# Privacy: 100% private, offline
# Latency: 5-15 seconds (once warmed up)
```

---

## 🎯 Next Steps

1. Install Ollama
2. Run `ollama serve`
3. Download Mistral: `ollama pull mistral`
4. Run test script: `python test_ollama.py`
5. Start backend: `uvicorn app.main:app --reload`

Your backend is now using **free, private, local AI** instead of OpenAI! 🎉

---

## 📚 Additional Resources

- **Ollama Docs**: https://github.com/ollama/ollama
- **Mistral Model**: https://mistral.ai
- **Model Library**: https://ollama.ai/library

---

**Questions?** Check the troubleshooting section above or consult the Ollama documentation.
