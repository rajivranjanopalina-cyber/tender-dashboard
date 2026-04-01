import os
import pytest
import bcrypt


def test_verify_password_correct():
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["DASHBOARD_PASSWORD_HASH"] = bcrypt.hashpw(b"mypassword", bcrypt.gensalt()).decode()

    from backend.auth import verify_password
    assert verify_password("mypassword") is True


def test_verify_password_wrong():
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["DASHBOARD_PASSWORD_HASH"] = bcrypt.hashpw(b"mypassword", bcrypt.gensalt()).decode()

    from backend.auth import verify_password
    assert verify_password("wrongpassword") is False


def test_create_and_decode_jwt():
    os.environ["JWT_SECRET"] = "test-jwt-secret"

    from backend.auth import create_jwt, decode_jwt
    token = create_jwt(remember_me=False)
    payload = decode_jwt(token)
    assert payload is not None
    assert "exp" in payload


def test_expired_jwt_returns_none():
    os.environ["JWT_SECRET"] = "test-jwt-secret"

    from backend.auth import create_jwt, decode_jwt
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    payload = {"exp": datetime.now(timezone.utc) - timedelta(hours=1)}
    token = pyjwt.encode(payload, "test-jwt-secret", algorithm="HS256")
    assert decode_jwt(token) is None
