import os
import pytest


@pytest.fixture(autouse=True)
def restore_database_module():
    """Reload backend.database after each test to restore clean module state.

    importlib.reload() in these tests replaces the module-level Base and engine
    objects.  Other tests import Base from backend.database via conftest; if the
    module is left in a partially-initialised (Turso) state, those tests fail
    with "no such table" errors because Base.metadata has no registered models.
    This fixture reloads the module with no Turso vars set and then reloads
    backend.models so that ORM model classes re-register against the fresh Base.
    """
    yield
    import importlib
    import sys

    # Remove Turso vars so reload uses SQLite
    os.environ.pop("TURSO_DATABASE_URL", None)
    os.environ.pop("TURSO_AUTH_TOKEN", None)

    # Reload config first, then database, then models
    import backend.config
    importlib.reload(backend.config)

    import backend.database
    importlib.reload(backend.database)

    # Reload models so their class definitions re-run against the new Base,
    # re-populating Base.metadata with all table definitions.
    import backend.models
    importlib.reload(backend.models)


def test_database_url_uses_turso_when_configured(monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://test.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("SECRET_KEY", "test")

    import importlib
    import backend.config
    importlib.reload(backend.config)

    import backend.database
    importlib.reload(backend.database)

    # With libsql_experimental + creator pattern, engine URL is sqlite://
    # but the creator connects to Turso via HTTP under the hood
    url = str(backend.database.engine.url)
    assert url == "sqlite://"


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
