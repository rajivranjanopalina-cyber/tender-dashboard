import os
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt


def verify_password(plaintext: str) -> bool:
    """Check plaintext password against DASHBOARD_PASSWORD_HASH env var."""
    stored_hash = os.environ.get("DASHBOARD_PASSWORD_HASH", "")
    if not stored_hash:
        return False
    return bcrypt.checkpw(plaintext.encode(), stored_hash.encode())


def create_jwt(remember_me: bool = False) -> str:
    """Create a signed JWT token. 7 days if remember_me, else 24 hours."""
    secret = os.environ.get("JWT_SECRET", "")
    expiry = timedelta(days=7) if remember_me else timedelta(hours=24)
    payload = {
        "exp": datetime.now(timezone.utc) + expiry,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_jwt(token: str) -> dict | None:
    """Decode and verify a JWT token. Returns payload or None if invalid/expired."""
    secret = os.environ.get("JWT_SECRET", "")
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
