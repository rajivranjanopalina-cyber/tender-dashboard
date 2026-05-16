import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.scraper.engine import run_all_portals

router = APIRouter()


def _require_cron_auth(request: Request) -> None:
    """
    Accept requests from Vercel cron scheduler (or manual trigger via SCRAPE_SECRET).
    Vercel sends: Authorization: Bearer <CRON_SECRET>
    We reuse SCRAPE_SECRET as the cron secret to keep env vars minimal.
    """
    secret = os.environ.get("SCRAPE_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="SCRAPE_SECRET not configured")

    auth_header = request.headers.get("Authorization", "")
    # Accept both "Bearer <secret>" (Vercel standard) and bare secret
    token = auth_header.removeprefix("Bearer ").strip()

    if token != secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@router.get("/scrape")
def cron_scrape(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(_require_cron_auth),
):
    """
    Scheduled daily scrape of all enabled portals.
    Called by Vercel Cron (configured in vercel.json).
    """
    run_all_portals(db=db)
    return {"status": "ok", "message": "Scrape completed"}
