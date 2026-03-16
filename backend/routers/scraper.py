from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models
from backend.schemas import ScrapeRunRequest, ScrapeLogOut, ScraperStatusOut, PaginatedResponse
from backend import scheduler

router = APIRouter()


@router.get("/status", response_model=ScraperStatusOut)
def get_status():
    return ScraperStatusOut(
        is_running=scheduler.get_is_running(),
        next_run_at=scheduler.get_next_run_time(),
    )


@router.post("/run", status_code=202)
def trigger_scrape(data: ScrapeRunRequest):
    started = scheduler.trigger_scrape(portal_id=data.portal_id)
    if not started:
        raise HTTPException(status_code=409, detail="A scrape is already in progress")
    return {"message": "Scrape started"}


@router.get("/logs", response_model=PaginatedResponse)
def list_logs(page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    page_size = min(page_size, 200)
    total = db.query(models.ScrapeLog).count()
    items = (
        db.query(models.ScrapeLog)
        .order_by(models.ScrapeLog.run_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    out = []
    for log in items:
        out.append(ScrapeLogOut(
            id=log.id,
            portal_id=log.portal_id,
            portal_name=log.portal.name if log.portal else "",
            run_at=log.run_at,
            tenders_found=log.tenders_found,
            tenders_new=log.tenders_new,
            status=log.status,
            error_message=log.error_message,
        ).model_dump())
    return PaginatedResponse(items=out, total=total, page=page, page_size=page_size)
