"""Quick test to verify imports work."""

import sys
print("Testing imports...")

try:
    from app.models.summary import SummaryResponse, SummaryMetadata
    print("✓ Summary models imported")
except Exception as e:
    print(f"✗ Failed to import summary models: {e}")
    sys.exit(1)

try:
    from app.prompts.summary_prompts import format_daily_prompt, format_weekly_prompt
    print("✓ Summary prompts imported")
except Exception as e:
    print(f"✗ Failed to import summary prompts: {e}")
    sys.exit(1)

try:
    from app.services.log_accumulator import LogAccumulator
    print("✓ LogAccumulator imported")
except Exception as e:
    print(f"✗ Failed to import LogAccumulator: {e}")
    sys.exit(1)

try:
    from app.services.summary_service import SummaryService
    print("✓ SummaryService imported")
except Exception as e:
    print(f"✗ Failed to import SummaryService: {e}")
    sys.exit(1)

try:
    from app.api.routes import summary
    print("✓ Summary routes imported")
except Exception as e:
    print(f"✗ Failed to import summary routes: {e}")
    sys.exit(1)

print("\n✓ All imports successful!")
print("\nSummary system ready to use:")
print("  - GET /api/summary/yesterday")
print("  - GET /api/summary/today")
print("  - GET /api/summary/week?start_date=YYYY-MM-DD")
print("  - GET /api/summary/date/{date}")
