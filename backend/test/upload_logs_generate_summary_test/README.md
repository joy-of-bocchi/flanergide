# Summary System Test Files

This directory contains test files for the summary system.

## Files

- **test_logs.json** - Sample phone log data for testing
- **test.ps1** - PowerShell script to run automated test
- **quick_test.py** - Python script that generates test commands
- **test_summary_endpoints.py** - Full automated test (requires dependencies)
- **test_commands.sh** - Bash script with test commands
- **test_imports.py** - Verify Python imports work correctly

## Documentation

- **COMMENTARY_SYSTEM.md** - Complete system documentation
- **TEST_GUIDE.md** - Step-by-step testing guide

## Quick Test

```powershell
# Generate a token first
cd ../..
.\venv\Scripts\Activate.ps1
python generate_token.py test-device "Test Device" --no-expiry

# Run the test
cd test/upload_logs_generate_summary_test
..\..\..\test.ps1 "YOUR_TOKEN_HERE"
```

## What Gets Tested

1. Upload 8 sample text logs to the server
2. Generate AI summary for the day
3. Verify files created in `app/storage/analysis/YYYY-MM-DD/`
   - daily.log (accumulated logs)
   - summary.md (AI-generated analysis)
