import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Check Turso DB and Vercel Blob connectivity."""
    checks = {}

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check Blob storage (just verify token is set)
    blob_token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
    checks["blob_storage"] = "ok" if blob_token else "warning: BLOB_READ_WRITE_TOKEN not set"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
