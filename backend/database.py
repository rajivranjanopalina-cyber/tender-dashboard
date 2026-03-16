import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _get_database_url() -> str:
    import tempfile
    data_dir = os.environ.get("DATA_DIR", "/data")
    try:
        os.makedirs(data_dir, exist_ok=True)
    except OSError:
        # Fallback for environments where /data is not writable (e.g., dev/test host)
        data_dir = tempfile.mkdtemp(prefix="tender_")
    return f"sqlite:///{data_dir}/tender.db"


engine = create_engine(
    _get_database_url(),
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


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
