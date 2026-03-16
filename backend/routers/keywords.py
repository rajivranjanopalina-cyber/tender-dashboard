from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.database import get_db
from backend import models
from backend.schemas import KeywordCreate, KeywordUpdate, KeywordOut, PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
def list_keywords(page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    page_size = min(page_size, 200)
    total = db.query(models.Keyword).count()
    items = db.query(models.Keyword).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[KeywordOut.model_validate(k).model_dump() for k in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=KeywordOut, status_code=201)
def create_keyword(data: KeywordCreate, db: Session = Depends(get_db)):
    kw = models.Keyword(value=data.value, active=data.active)
    db.add(kw)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Keyword already exists")
    db.refresh(kw)
    return KeywordOut.model_validate(kw)


@router.put("/{kw_id}", response_model=KeywordOut)
def update_keyword(kw_id: int, data: KeywordUpdate, db: Session = Depends(get_db)):
    kw = db.get(models.Keyword, kw_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    if data.value is not None:
        kw.value = data.value
    if data.active is not None:
        kw.active = data.active
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Keyword value already exists")
    db.refresh(kw)
    return KeywordOut.model_validate(kw)


@router.delete("/{kw_id}", status_code=204)
def delete_keyword(kw_id: int, db: Session = Depends(get_db)):
    kw = db.get(models.Keyword, kw_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(kw)
    db.commit()
