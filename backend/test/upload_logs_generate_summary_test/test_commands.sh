#!/bin/bash
# Test commands for summary system
# Replace YOUR_JWT_TOKEN with an actual token from your server

echo "=================================="
echo "SUMMARIZATION SYSTEM TEST COMMANDS"
echo "=================================="
echo ""

# Get current timestamp
NOW=$(date +%s)000

echo "1. Upload test logs"
echo "-----------------------------------"
cat << 'EOF'
curl -X POST "http://localhost:8000/api/logs/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
  "logs": [
    {
      "text": "Working on the summary system implementation. Building API endpoints and services.",
      "appPackage": "com.android.vscode",
      "timestamp": 1731686400000,
      "deviceId": "test-device-001"
    },
    {
      "text": "Researching how to integrate ChromaDB with LLM-based analysis",
      "appPackage": "com.brave.browser",
      "timestamp": 1731682800000,
      "deviceId": "test-device-001"
    },
    {
      "text": "hey what time should we meet for lunch?",
      "appPackage": "com.instagram.android",
      "timestamp": 1731679200000,
      "deviceId": "test-device-001"
    },
    {
      "text": "Debugging the log accumulator service. Fixed file path issues.",
      "appPackage": "com.android.vscode",
      "timestamp": 1731675600000,
      "deviceId": "test-device-001"
    },
    {
      "text": "Reading documentation about vector databases and embeddings",
      "appPackage": "com.brave.browser",
      "timestamp": 1731672000000,
      "deviceId": "test-device-001"
    }
  ]
}'
EOF

echo ""
echo ""
echo "2. Generate today's summary"
echo "-----------------------------------"
echo 'curl -X GET "http://localhost:8000/api/summary/today" \'
echo '  -H "Authorization: Bearer YOUR_JWT_TOKEN" | python -m json.tool'

echo ""
echo ""
echo "3. Generate yesterday's summary"
echo "-----------------------------------"
echo 'curl -X GET "http://localhost:8000/api/summary/yesterday" \'
echo '  -H "Authorization: Bearer YOUR_JWT_TOKEN" | python -m json.tool'

echo ""
echo ""
echo "4. Generate weekly summary"
echo "-----------------------------------"
echo 'curl -X GET "http://localhost:8000/api/summary/week" \'
echo '  -H "Authorization: Bearer YOUR_JWT_TOKEN" | python -m json.tool'

echo ""
echo ""
echo "=================================="
echo "FILES TO CHECK AFTER RUNNING:"
echo "=================================="
echo "After running the summary commands, check these directories:"
echo ""
echo "  backend/app/storage/analysis/$(date +%Y-%m-%d)/"
echo "    - daily.log"
echo "    - summary.md"
echo ""
