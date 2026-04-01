import os
import uuid
import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Set env vars BEFORE any backend imports so settings singleton reads them
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-bytes-padding!")

# JWT auth env vars — set early so auth module picks them up
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["DASHBOARD_PASSWORD_HASH"] = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()

# Import backend modules ONCE at conftest load time so we always hold the
# original function/class references that the routers also imported.
# test_database_turso.py reloads backend.database which would create new
# get_db/Base objects; using the originals ensures overrides apply correctly.
from backend.database import Base as _Base, get_db as _get_db  # noqa: E402
from backend import main as _main  # ensure app and routers are registered  # noqa: F401, E402


def _make_engine():
    """
    Create a truly isolated in-memory SQLite test engine.
    Uses a unique named in-memory database so each test gets its own database.
    """
    # Import current Base for schema — but use create_all on the original
    # metadata (which is what the routers reference via their model imports).
    db_name = f"test_{uuid.uuid4().hex}"
    url = f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true"
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "uri": True},
    )
    # Apply FK pragma to test engines (mirrors production behaviour)
    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    # Use _Base (original metadata) to ensure table definitions match what
    # the ORM models expect, regardless of any later module reloads.
    _Base.metadata.create_all(bind=engine)
    return engine


def _make_jwt() -> str:
    """Create a valid JWT token for test auth using the canonical test JWT secret."""
    from backend.auth import create_jwt
    old = os.environ.get("JWT_SECRET", "")
    os.environ["JWT_SECRET"] = "test-jwt-secret"
    token = create_jwt(remember_me=False)
    os.environ["JWT_SECRET"] = old if old else "test-jwt-secret"
    return token


@pytest.fixture(scope="function")
def db_engine():
    engine = _make_engine()
    yield engine
    _Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()  # prevent state bleed
    session.close()


@pytest.fixture(scope="function")
def client(db_engine):
    from backend.main import app

    # Ensure all model tables exist on the test engine
    _Base.metadata.create_all(bind=db_engine)

    def override_get_db():
        Session = sessionmaker(bind=db_engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()

    # Use the ORIGINAL get_db reference (same one routers imported at load time)
    # so the dependency override is applied to the correct dependency key.
    app.dependency_overrides[_get_db] = override_get_db

    token = _make_jwt()
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as c:
        yield c
    app.dependency_overrides.clear()
