from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models
from backend.schemas import PortalCreate, PortalUpdate, PortalOut, PaginatedResponse
from backend.encryption import encrypt_password

router = APIRouter()


def portal_to_out(portal: models.Portal) -> PortalOut:
    return PortalOut(
        id=portal.id,
        name=portal.name,
        url=portal.url,
        enabled=portal.enabled,
        requires_auth=portal.requires_auth,
        username=portal.username,
        last_scraped_at=portal.last_scraped_at,
        scrape_config=portal.scrape_config,
        created_at=portal.created_at,
        has_password=portal.password_enc is not None,
    )


@router.get("", response_model=PaginatedResponse)
def list_portals(page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    page_size = min(page_size, 200)
    total = db.query(models.Portal).count()
    items = db.query(models.Portal).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[portal_to_out(p).model_dump() for p in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{portal_id}", response_model=PortalOut)
def get_portal(portal_id: int, db: Session = Depends(get_db)):
    portal = db.get(models.Portal, portal_id)
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")
    return portal_to_out(portal)


@router.post("", response_model=PortalOut, status_code=201)
def create_portal(data: PortalCreate, db: Session = Depends(get_db)):
    portal = models.Portal(
        name=data.name, url=data.url, enabled=data.enabled,
        requires_auth=data.requires_auth, username=data.username,
        password_enc=encrypt_password(data.password) if data.password else None,
        scrape_config=data.scrape_config,
    )
    db.add(portal)
    db.commit()
    db.refresh(portal)
    return portal_to_out(portal)


@router.put("/{portal_id}", response_model=PortalOut)
def update_portal(portal_id: int, data: PortalUpdate, db: Session = Depends(get_db)):
    portal = db.get(models.Portal, portal_id)
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")
    if data.name is not None:
        portal.name = data.name
    if data.url is not None:
        portal.url = data.url
    if data.enabled is not None:
        portal.enabled = data.enabled
    if data.requires_auth is not None:
        portal.requires_auth = data.requires_auth
    if data.username is not None:
        portal.username = data.username
    if data.password is not None:
        portal.password_enc = encrypt_password(data.password)
    if data.scrape_config is not None:
        portal.scrape_config = data.scrape_config
    db.commit()
    db.refresh(portal)
    return portal_to_out(portal)


@router.delete("/{portal_id}", status_code=204)
def delete_portal(portal_id: int, db: Session = Depends(get_db)):
    portal = db.get(models.Portal, portal_id)
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")
    # Cascade: delete associated tenders (and their proposals) and scrape logs first
    # to avoid FK constraint violations (PRAGMA foreign_keys=ON is active)
    for tender in portal.tenders:
        for proposal in tender.proposals:
            db.delete(proposal)
        db.delete(tender)
    for log in portal.scrape_logs:
        db.delete(log)
    db.delete(portal)
    db.commit()
