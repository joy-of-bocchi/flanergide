"""Quick test without requiring venv activation."""
import json
import subprocess
import sys
from datetime import datetime

print("=" * 80)
print("SUMMARIZATION SYSTEM QUICK TEST")
print("=" * 80)

# Check if server is running
print("\n1. Checking if server is running...")
try:
    result = subprocess.run(
        ['curl', '-s', 'http://localhost:8000/api/health'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if "ok" in result.stdout:
        print("[OK] Server is running!")
    else:
        print("[ERROR] Server not responding correctly")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] Cannot reach server: {e}")
    print("Make sure your FastAPI server is running on port 8000")
    sys.exit(1)

# Read test data
print("\n2. Loading test data...")
with open('test_logs.json', 'r') as f:
    test_data = json.load(f)
print(f"[OK] Loaded {len(test_data['logs'])} test log entries")

# Instructions for getting token
print("\n" + "=" * 80)
print("MANUAL STEPS REQUIRED")
print("=" * 80)
print("\nYou need a JWT token to continue. Get one by either:")
print("\n  Option 1: If you have an existing token, set it as environment variable:")
print("    export TEST_TOKEN='your_token_here'  # Linux/Mac")
print("    set TEST_TOKEN=your_token_here       # Windows")
print("\n  Option 2: Generate a new token (requires venv):")
print("    cd backend")
print("    venv\\Scripts\\activate              # Windows")
print("    python generate_token.py test-device 'Test Device' --no-expiry")
print("\nThen run these commands:")
print("\n" + "=" * 80)

# Generate curl commands
today = datetime.now().strftime("%Y-%m-%d")

print("\n# Step 1: Upload test logs")
print("-" * 80)
print(f"curl -X POST 'http://localhost:8000/api/logs/upload' \\")
print(f"  -H 'Authorization: Bearer YOUR_TOKEN_HERE' \\")
print(f"  -H 'Content-Type: application/json' \\")
print(f"  -d @test_logs.json")

print("\n# Step 2: Generate today's summary")
print("-" * 80)
print(f"curl -X GET 'http://localhost:8000/api/summary/today' \\")
print(f"  -H 'Authorization: Bearer YOUR_TOKEN_HERE' \\")
print(f"  -s | python -m json.tool")

print("\n# Step 3: Check the generated files")
print("-" * 80)
print(f"cat app/storage/analysis/{today}/daily.log")
print(f"cat app/storage/analysis/{today}/summary.md")

print("\n" + "=" * 80)
print("OR: Use PowerShell to test (Windows)")
print("=" * 80)
print(f"""
$token = "YOUR_TOKEN_HERE"
$headers = @{{"Authorization" = "Bearer $token"}}

# Upload logs
$body = Get-Content test_logs.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "http://localhost:8000/api/logs/upload" -Method Post -Headers $headers -Body $body -ContentType "application/json"

# Get summary
Invoke-RestMethod -Uri "http://localhost:8000/api/summary/today" -Method Get -Headers $headers
""")

print("\n" + "=" * 80)
print("After running the commands, check these files:")
print("=" * 80)
print(f"  1. app\\storage\\analysis\\{today}\\daily.log")
print(f"  2. app\\storage\\analysis\\{today}\\summary.md")
print("\n")
