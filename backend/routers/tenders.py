import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models
from backend.schemas import TenderOut, TenderUpdate, PaginatedResponse

router = APIRouter()


def tender_to_out(tender: models.Tender) -> dict:
    return TenderOut(
        id=tender.id,
        portal_id=tender.portal_id,
        portal_name=tender.portal.name if tender.portal else "",
        title=tender.title,
        description=tender.description,
        published_date=tender.published_date,
        deadline=tender.deadline,
        estimated_value=tender.estimated_value,
        source_url=tender.source_url,
        matched_keywords=tender.matched_keywords,
        status=tender.status,
        notes=tender.notes,
        scraped_at=tender.scraped_at,
        last_updated_at=tender.last_updated_at,
    ).model_dump()


@router.get("", response_model=PaginatedResponse)
def list_tenders(
    page: int = 1,
    page_size: int = 50,
    portal_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    scraped_from: Optional[str] = None,  # ISO datetime — filters on scraped_at
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    page_size = min(page_size, 200)
    q = db.query(models.Tender)
    if portal_id:
        q = q.filter(models.Tender.portal_id == portal_id)
    if status:
        q = q.filter(models.Tender.status == status)
    if date_from:
        q = q.filter(models.Tender.deadline >= date_from)
    if date_to:
        q = q.filter(models.Tender.deadline <= date_to)
    if scraped_from:
        q = q.filter(models.Tender.scraped_at >= scraped_from)
    if keyword:
        # Filter tenders where matched_keywords JSON array contains the keyword (case-insensitive)
        q = q.filter(models.Tender.matched_keywords.ilike(f'%"{keyword}"%'))
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(items=[tender_to_out(t) for t in items], total=total, page=page, page_size=page_size)


@router.get("/{tender_id}")
def get_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    # Auto-transition new → under_review on first view
    if tender.status == "new":
        tender.status = "under_review"
        tender.last_updated_at = datetime.utcnow()
        db.commit()
        db.refresh(tender)
    return tender_to_out(tender)


@router.put("/{tender_id}")
def update_tender(tender_id: int, data: TenderUpdate, db: Session = Depends(get_db)):
    tender = db.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if data.status is not None:
        tender.status = data.status
    if data.notes is not None:
        tender.notes = data.notes
    tender.last_updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tender)
    return tender_to_out(tender)


@router.delete("/{tender_id}", status_code=204)
def delete_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.get(models.Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.proposals:
        raise HTTPException(status_code=409, detail="Delete all associated proposals before deleting this tender")
    db.delete(tender)
    db.commit()
