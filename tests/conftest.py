import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set env vars BEFORE any backend imports so settings singleton reads them
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-bytes-padding!")
# DATA_DIR set per-test via monkeypatch; leave unset here so test_config can test defaults

# NOTE: backend.database and backend.main are imported lazily inside fixtures
# so that earlier tasks (Tasks 2-4) can run tests without main.py existing yet.


def _make_engine():
    from backend.database import Base
    # StaticPool ensures all connections — including those made by FastAPI TestClient
    # worker threads — share the exact same underlying DBAPI connection, giving
    # each test function a fully isolated in-memory database without URI tricks.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Apply FK pragma to test engines (mirrors production behaviour)
    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(bind=engine)
    return engine, Base  # return Base to avoid re-importing in caller


@pytest.fixture(scope="function")
def db_engine():
    engine, Base = _make_engine()
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()  # prevent state bleed
    session.close()


@pytest.fixture(scope="function")
def client(db_engine):
    from backend.database import get_db, Base
    from backend.main import app  # importing main registers all models to Base

    # Ensure all model tables exist on the test engine (models register to Base
    # only when backend.main is imported; _make_engine runs create_all too early).
    Base.metadata.create_all(bind=db_engine)

    def override_get_db():
        Session = sessionmaker(bind=db_engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
