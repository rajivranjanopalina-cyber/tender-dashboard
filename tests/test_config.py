import os
import pytest


def test_settings_loads_turso_vars(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://test.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("JWT_SECRET", "jwt-test-secret")
    monkeypatch.setenv("DASHBOARD_PASSWORD_HASH", "$2b$12$fakehash")
    monkeypatch.setenv("SCRAPE_SECRET", "scrape-test-secret")

    import importlib
    import backend.config
    importlib.reload(backend.config)
    s = backend.config.Settings()

    assert s.turso_database_url == "libsql://test.turso.io"
    assert s.turso_auth_token == "test-token"
    assert s.jwt_secret == "jwt-test-secret"
    assert s.dashboard_password_hash == "$2b$12$fakehash"
    assert s.scrape_secret == "scrape-test-secret"
