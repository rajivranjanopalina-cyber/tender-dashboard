import os
import pytest
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Set env vars BEFORE any backend imports so settings singleton reads them
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-bytes-padding!")
# DATA_DIR set per-test via monkeypatch; leave unset here so test_config can test defaults

# NOTE: backend.database and backend.main are imported lazily inside fixtures
# so that earlier tasks (Tasks 2-4) can run tests without main.py existing yet.


def _make_engine():
    from backend.database import Base
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Apply FK pragma to test engines (mirrors production behaviour)
    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_engine():
    engine = _make_engine()
    from backend.database import Base
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_engine):
    from backend.database import get_db
    from backend.main import app

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
