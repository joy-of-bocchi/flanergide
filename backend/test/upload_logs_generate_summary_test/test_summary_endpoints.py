"""Test script for summary endpoints."""

import asyncio
import json
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, ".")

from app.api.middleware.auth import create_access_token
from app.config import settings


async def main():
    """Test summary system."""

    print("=" * 80)
    print("TESTING SUMMARIZATION SYSTEM")
    print("=" * 80)

    # Step 1: Generate JWT token
    print("\n1. Generating JWT token...")
    token, expiry = create_access_token(
        device_id="test-device-001",
        device_name="Test Device",
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
        expiry_hours=24
    )
    print(f"OK Token generated: {token[:50]}...")

    # Step 2: Create test log data
    print("\n2. Creating test log data...")
    now_timestamp = int(datetime.now().timestamp() * 1000)

    test_logs = [
        {
            "text": "Working on the summary system implementation. Building API endpoints and services.",
            "appPackage": "com.android.vscode",
            "timestamp": now_timestamp - 3600000,  # 1 hour ago
            "deviceId": "test-device-001"
        },
        {
            "text": "Researching how to integrate ChromaDB with LLM-based analysis",
            "appPackage": "com.brave.browser",
            "timestamp": now_timestamp - 7200000,  # 2 hours ago
            "deviceId": "test-device-001"
        },
        {
            "text": "hey what time should we meet for lunch?",
            "appPackage": "com.instagram.android",
            "timestamp": now_timestamp - 10800000,  # 3 hours ago
            "deviceId": "test-device-001"
        },
        {
            "text": "Debugging the log accumulator service. Fixed file path issues.",
            "appPackage": "com.android.vscode",
            "timestamp": now_timestamp - 14400000,  # 4 hours ago
            "deviceId": "test-device-001"
        },
        {
            "text": "Reading documentation about vector databases and embeddings",
            "appPackage": "com.brave.browser",
            "timestamp": now_timestamp - 18000000,  # 5 hours ago
            "deviceId": "test-device-001"
        },
    ]

    print(f"OK Created {len(test_logs)} test log entries")

    # Step 3: Generate curl command for log upload
    print("\n3. Uploading test logs...")
    print("\nRun this command to upload logs:")
    print("-" * 80)

    upload_data = json.dumps({"logs": test_logs}, indent=2)

    curl_upload = f'''curl -X POST "http://localhost:8000/api/logs/upload" \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{upload_data}' '''

    print(curl_upload)
    print("-" * 80)

    # Step 4: Generate curl commands for summary endpoints
    print("\n4. Testing summary endpoints...")
    print("\nAfter uploading logs, run these commands:\n")

    print("# Get today's summary:")
    print(f'curl -X GET "http://localhost:8000/api/summary/today" -H "Authorization: Bearer {token}" | python -m json.tool')

    print("\n# Get yesterday's summary:")
    print(f'curl -X GET "http://localhost:8000/api/summary/yesterday" -H "Authorization: Bearer {token}" | python -m json.tool')

    print("\n# Get weekly summary:")
    print(f'curl -X GET "http://localhost:8000/api/summary/week" -H "Authorization: Bearer {token}" | python -m json.tool')

    print("\n" + "=" * 80)
    print("AUTOMATED TEST")
    print("=" * 80)

    # Try to upload logs automatically using httpx
    try:
        import httpx

        print("\n5. Attempting automatic upload...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/logs/upload",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"logs": test_logs},
                timeout=30.0
            )

            if response.status_code == 201:
                result = response.json()
                print(f"OK Upload successful!")
                print(f"  - Uploaded: {result['uploaded']}")
                print(f"  - Failed: {result['failed']}")
                print(f"  - Status: {result['status']}")
                print(f"  - Message: {result['message']}")

                # Now try to generate summary
                print("\n6. Generating today's summary...")
                summary_response = await client.get(
                    "http://localhost:8000/api/summary/today",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=120.0  # Longer timeout for LLM
                )

                if summary_response.status_code == 200:
                    summary_result = summary_response.json()
                    print("OK Summary generated successfully!")
                    print(f"\nMetadata:")
                    print(f"  - Date: {summary_result['metadata']['date_range']}")
                    print(f"  - Log count: {summary_result['metadata']['log_count']}")
                    print(f"  - Blog count: {summary_result['metadata']['blog_count']}")
                    print(f"  - Analysis type: {summary_result['metadata']['analysis_type']}")
                    print(f"\nLog file: {summary_result['log_file_path']}")
                    print(f"Summary file: {summary_result['summary_file_path']}")

                    print("\n" + "=" * 80)
                    print("SUMMARY PREVIEW (first 500 chars):")
                    print("=" * 80)
                    print(summary_result['summary'][:500])
                    print("...")
                    print("=" * 80)

                    print("\nOKOKOK TEST SUCCESSFUL! OKOKOK")
                    print(f"\nCheck these files:")
                    print(f"  1. {summary_result['log_file_path']}")
                    print(f"  2. {summary_result['summary_file_path']}")

                else:
                    print(f"ERROR Summary generation failed: {summary_response.status_code}")
                    print(f"Response: {summary_response.text}")
            else:
                print(f"ERROR Upload failed: {response.status_code}")
                print(f"Response: {response.text}")

    except ImportError:
        print("\n⚠ httpx not installed, skipping automated test")
        print("Run the curl commands above manually")
    except Exception as e:
        print(f"\nERROR Automated test failed: {e}")
        print("Run the curl commands above manually")


if __name__ == "__main__":
    asyncio.run(main())
