import os
import bcrypt
import pytest


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("DASHBOARD_PASSWORD_HASH", bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode())



def test_login_success(client):
    resp = client.post("/api/auth", json={"password": "testpass"})
    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password(client):
    resp = client.post("/api/auth", json={"password": "wrong"})
    assert resp.status_code == 401


def test_protected_endpoint_without_token(client):
    resp = client.get("/api/keywords")
    assert resp.status_code == 401


def test_protected_endpoint_with_valid_token(client):
    login_resp = client.post("/api/auth", json={"password": "testpass"})
    token = login_resp.json()["token"]
    resp = client.get("/api/keywords", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
