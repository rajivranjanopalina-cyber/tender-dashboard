import os
import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend import models
from backend.schemas import ScrapeRunRequest, ScrapeLogOut, PaginatedResponse

router = APIRouter()

# Note: Scrape token auth is handled by require_auth in dependencies.py
# which checks X-Scrape-Token header for /scraper/ paths.


@router.get("/status")
def get_scrape_status(db: Session = Depends(get_db)):
    """Get latest ScrapeLog per portal."""
    subq = (
        db.query(models.ScrapeLog.portal_id, func.max(models.ScrapeLog.run_at).label("max_run"))
        .group_by(models.ScrapeLog.portal_id)
        .subquery()
    )
    logs = (
        db.query(models.ScrapeLog)
        .join(subq, (models.ScrapeLog.portal_id == subq.c.portal_id) & (models.ScrapeLog.run_at == subq.c.max_run))
        .all()
    )
    return [
        ScrapeLogOut(
            id=log.id, portal_id=log.portal_id,
            portal_name=log.portal.name if log.portal else "",
            run_at=log.run_at, tenders_found=log.tenders_found,
            tenders_new=log.tenders_new, status=log.status,
            error_message=log.error_message,
        ).model_dump()
        for log in logs
    ]


@router.post("/run", status_code=202)
async def trigger_scrape(data: ScrapeRunRequest, request: Request, db: Session = Depends(get_db)):
    """
    Trigger scrape. With portal_id: scrape one portal directly.
    Without portal_id: fan-out to all active portals using async concurrency.
    """
    if data.portal_id:
        from backend.scraper.engine import scrape_portal
        scrape_portal(portal_id=data.portal_id, db=db)
        return {"message": f"Scrape completed for portal {data.portal_id}"}

    # Fan-out: fire async requests for each active portal
    import asyncio
    portals = db.query(models.Portal).filter(models.Portal.enabled == True).all()
    vercel_url = os.environ.get("VERCEL_URL", "localhost:3000")
    scrape_secret = os.environ.get("SCRAPE_SECRET", "")
    auth_header = request.headers.get("Authorization", "")

    async def fire_scrape(portal_id: int):
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    f"https://{vercel_url}/api/scraper/run",
                    json={"portal_id": portal_id},
                    headers={
                        "Authorization": auth_header,
                        "X-Scrape-Token": scrape_secret,
                    },
                    timeout=1.0,
                )
            except (httpx.TimeoutException, httpx.ConnectError):
                pass  # Fire and forget

    BATCH_SIZE = 10
    triggered = []
    for i in range(0, len(portals), BATCH_SIZE):
        batch = portals[i:i + BATCH_SIZE]
        await asyncio.gather(*[fire_scrape(p.id) for p in batch])
        triggered.extend([p.id for p in batch])

    return {"message": f"Fan-out triggered for {len(triggered)} portals", "portal_ids": triggered}


@router.get("/logs", response_model=PaginatedResponse)
def list_logs(page: int = 1, page_size: int = 50, portal_id: int = None, db: Session = Depends(get_db)):
    page_size = min(page_size, 200)
    query = db.query(models.ScrapeLog)
    if portal_id:
        query = query.filter(models.ScrapeLog.portal_id == portal_id)
    total = query.count()
    items = (
        query.order_by(models.ScrapeLog.run_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    out = []
    for log in items:
        out.append(ScrapeLogOut(
            id=log.id, portal_id=log.portal_id,
            portal_name=log.portal.name if log.portal else "",
            run_at=log.run_at, tenders_found=log.tenders_found,
            tenders_new=log.tenders_new, status=log.status,
            error_message=log.error_message,
        ).model_dump())
    return PaginatedResponse(items=out, total=total, page=page, page_size=page_size)
