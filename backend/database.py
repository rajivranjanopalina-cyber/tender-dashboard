import os
import tempfile
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _get_database_url() -> str:
    """Use Turso if configured, otherwise fall back to local SQLite."""
    turso_url = os.environ.get("TURSO_DATABASE_URL", "")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN", "")

    if turso_url and turso_token:
        # turso_url is like "libsql://your-db.turso.io"
        # sqlalchemy-libsql expects "sqlite+libsql://your-db.turso.io?authToken=...&secure=true"
        host = turso_url.replace("libsql://", "").replace("https://", "")
        return f"sqlite+libsql://{host}?authToken={turso_token}&secure=true"

    # Fallback to SQLite for local dev/testing
    data_dir = os.environ.get("DATA_DIR", tempfile.mkdtemp(prefix="tender_"))
    os.makedirs(data_dir, exist_ok=True)
    return f"sqlite:///{data_dir}/tender.db"


def _create_engine():
    url = _get_database_url()
    if url.startswith("sqlite+libsql"):
        return create_engine(url)
    else:
        eng = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return eng


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
