"""JWT authentication middleware."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def verify_jwt(
    credentials,
    jwt_secret: str,
    jwt_algorithm: str
) -> dict:
    """Verify JWT token and return claims.

    Args:
        credentials: HTTP authentication credentials
        jwt_secret: JWT secret key
        jwt_algorithm: JWT algorithm

    Returns:
        Decoded JWT payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        token = credentials.credentials
        # Add 5 hour leeway to handle time sync issues between client and server
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=[jwt_algorithm],
            options={"verify_iat": True},
            leeway=timedelta(hours=5)
        )
        device_id = payload.get("sub")
        if not device_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature"
        )
    except jwt.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


def create_access_token(
    device_id: str,
    device_name: Optional[str],
    jwt_secret: str,
    jwt_algorithm: str,
    expiry_hours: int
) -> tuple[str, int]:
    """Create a new JWT access token.

    Args:
        device_id: Device identifier
        device_name: Human-readable device name
        jwt_secret: JWT secret key
        jwt_algorithm: JWT algorithm
        expiry_hours: Token expiration time in hours

    Returns:
        Tuple of (token, expiry_timestamp)
    """
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=expiry_hours)

    payload = {
        "sub": device_id,
        "device_name": device_name or device_id,
        "iat": int(now.timestamp()),
        "exp": int(expiry.timestamp())
    }

    token = jwt.encode(
        payload,
        jwt_secret,
        algorithm=jwt_algorithm
    )

    logger.info(f"Created token for device {device_id}")
    return token, int(expiry.timestamp())


async def refresh_access_token(
    token: str,
    jwt_secret: str,
    jwt_algorithm: str,
    expiry_hours: int
) -> tuple[str, int]:
    """Refresh an access token.

    Args:
        token: Expired or valid token
        jwt_secret: JWT secret key
        jwt_algorithm: JWT algorithm
        expiry_hours: New token expiration time in hours

    Returns:
        Tuple of (new_token, expiry_timestamp)

    Raises:
        HTTPException: If token cannot be refreshed
    """
    try:
        # Decode without checking expiration
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=[jwt_algorithm],
            options={"verify_exp": False}
        )

        device_id = payload.get("sub")
        device_name = payload.get("device_name")

        if not device_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )

        # Create new token
        new_token, expiry = create_access_token(
            device_id=device_id,
            device_name=device_name,
            jwt_secret=jwt_secret,
            jwt_algorithm=jwt_algorithm,
            expiry_hours=expiry_hours
        )

        logger.info(f"Refreshed token for device {device_id}")
        return new_token, expiry

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cannot refresh token"
        )


async def extract_device_id(credentials) -> Optional[str]:
    """Extract device ID from JWT token without full validation.

    Useful for logging and tracking.

    Args:
        credentials: HTTP credentials

    Returns:
        Device ID, or None if extraction fails
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        # Decode without verification (just to extract claims)
        payload = jwt.decode(
            credentials.credentials,
            options={"verify_signature": False}
        )
        return payload.get("sub")
    except Exception:
        return None
