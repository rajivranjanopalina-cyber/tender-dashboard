import os
import pytest


def test_database_url_uses_turso_when_configured(monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://test.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("SECRET_KEY", "test")

    import importlib
    import backend.config
    importlib.reload(backend.config)

    import backend.database
    importlib.reload(backend.database)

    url = str(backend.database.engine.url)
    assert "libsql" in url or "turso" in url


def test_database_falls_back_to_sqlite_when_no_turso(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("SECRET_KEY", "test")

    import importlib
    import backend.config
    importlib.reload(backend.config)

    import backend.database
    importlib.reload(backend.database)

    url = str(backend.database.engine.url)
    assert "sqlite" in url
