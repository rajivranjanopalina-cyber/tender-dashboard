import os
import tempfile
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _create_engine():
    """Create SQLAlchemy engine — uses libsql_experimental for Turso (HTTP),
    falls back to plain SQLite for local dev/testing."""
    turso_url = os.environ.get("TURSO_DATABASE_URL", "").strip()
    turso_token = os.environ.get("TURSO_AUTH_TOKEN", "").strip()

    if turso_url and turso_token:
        # Use libsql_experimental which connects to Turso via HTTP
        # (sqlalchemy-libsql uses WebSocket which doesn't work on Vercel)
        import libsql_experimental as libsql

        host = turso_url.replace("libsql://", "").replace("https://", "")
        sync_url = f"https://{host}"

        local_db = os.path.join(tempfile.gettempdir(), "turso_local.db")

        def creator():
            conn = libsql.connect(local_db, sync_url=sync_url, auth_token=turso_token)
            conn.sync()
            # SQLAlchemy's SQLite dialect calls create_function for REGEXP support;
            # libsql_experimental doesn't implement it, so add a no-op stub.
            if not hasattr(conn, "create_function"):
                conn.create_function = lambda *args, **kwargs: None
            return conn

        return create_engine("sqlite://", creator=creator)

    # Fallback to SQLite for local dev/testing
    data_dir = os.environ.get("DATA_DIR", tempfile.mkdtemp(prefix="tender_"))
    os.makedirs(data_dir, exist_ok=True)
    url = f"sqlite:///{data_dir}/tender.db"
    eng = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_db_initialized = False


class Base(DeclarativeBase):
    pass


def init_db():
    global _db_initialized
    if _db_initialized:
        return
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _db_initialized = True


def get_db():
    init_db()  # lazy init on first request (safe for serverless)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
