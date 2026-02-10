from datetime import datetime, timedelta, timezone

import jwt
import uuid


def create_access_token(user_id, email, secret, ttl_minutes=15):
    """Create a short-lived access token for dual-token authentication."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token_string():
    """Generate a unique refresh token string (UUID-based)."""
    return str(uuid.uuid4())


def create_refresh_token_jwt(user_id, token_id, secret, ttl_days=7):
    """Create a refresh token JWT with specified TTL for dual-token authentication."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "jti": token_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=ttl_days),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token, secret):
    """Validate an access token and extract its payload."""
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        # Check if token has type field and is an access token
        if "type" in payload and payload.get("type") != "access":
            return None, f"Invalid token type: expected access, got {payload.get('type')}"
        return payload, None
    except jwt.PyJWTError as exc:
        return None, str(exc)


def decode_refresh_token(token, secret):
    """Validate a refresh token and extract its payload."""
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "jti", "type"]},
        )
        if payload.get("type") != "refresh":
            return None, "Invalid token type: expected refresh"
        return payload, None
    except jwt.PyJWTError as exc:
        return None, str(exc)
