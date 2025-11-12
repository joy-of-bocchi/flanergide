"""Generate JWT token for Android device authentication."""

import sys
import os
from datetime import datetime, timedelta
import jwt

# Load JWT secret from environment
from dotenv import load_dotenv
load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))

if not JWT_SECRET:
    print("Error: JWT_SECRET not found in .env file")
    sys.exit(1)

# Get device info from command line or use defaults
device_id = sys.argv[1] if len(sys.argv) > 1 else "android-device-001"
device_name = sys.argv[2] if len(sys.argv) > 2 else "My Android Phone"
never_expire = "--no-expiry" in sys.argv or "-n" in sys.argv

# Create JWT payload
now = datetime.utcnow()

payload = {
    "sub": device_id,  # Subject (device identifier)
    "device_name": device_name,
    "iat": int(now.timestamp()),  # Issued at
}

# Add expiration only if not requesting never-expire token
if not never_expire:
    expiry = now + timedelta(hours=TOKEN_EXPIRY_HOURS)
    payload["exp"] = int(expiry.timestamp())  # Expiration

# Generate token
token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

print("=" * 80)
print("JWT Token Generated Successfully!")
print("=" * 80)
print()
print(f"Device ID: {device_id}")
print(f"Device Name: {device_name}")
print(f"Issued At: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")

if never_expire:
    print(f"Expires At: NEVER (no expiration)")
    print(f"Valid For: FOREVER")
else:
    print(f"Expires At: {expiry.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Valid For: {TOKEN_EXPIRY_HOURS} hours")
print()
print("=" * 80)
print("TOKEN (copy this to your Android app):")
print("=" * 80)
print(token)
print("=" * 80)
print()
print("Android Usage:")
print("Add this to your app's HTTP headers:")
print(f'Authorization: Bearer {token}')
print()
if never_expire:
    print("WARNING: This token NEVER expires! Keep it extremely secure!")
else:
    print("WARNING: Keep this token secret! Anyone with this token can access your backend.")
print()
print("Usage Examples:")
print("  # Generate token that expires in 24 hours (default):")
print("  python generate_token.py \"device-id\" \"Device Name\"")
print()
print("  # Generate token that NEVER expires:")
print("  python generate_token.py \"device-id\" \"Device Name\" --no-expiry")
print("  python generate_token.py \"device-id\" \"Device Name\" -n")
print()
