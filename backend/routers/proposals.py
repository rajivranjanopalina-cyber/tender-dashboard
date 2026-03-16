import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models
from backend.schemas import ProposalCreate, ProposalOut, ProposalUpdate, PaginatedResponse

router = APIRouter()


def proposal_to_out(p: models.Proposal) -> dict:
    return ProposalOut(
        id=p.id,
        tender_id=p.tender_id,
        tender_title=p.tender.title if p.tender else "",
        template_id=p.template_id,
        template_name=p.template.name if p.template else None,
        file_path=p.file_path,
        status=p.status,
        created_at=p.created_at,
        updated_at=p.updated_at,
    ).model_dump()


@router.get("", response_model=PaginatedResponse)
def list_proposals(
    page: int = 1,
    page_size: int = 50,
    tender_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    page_size = min(page_size, 200)
    q = db.query(models.Proposal)
    if tender_id is not None:
        q = q.filter(models.Proposal.tender_id == tender_id)
    if status:
        q = q.filter(models.Proposal.status == status)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(items=[proposal_to_out(p) for p in items], total=total, page=page, page_size=page_size)


@router.post("", response_model=ProposalOut, status_code=201)
def create_proposal(data: ProposalCreate, db: Session = Depends(get_db)):
    tender = db.get(models.Tender, data.tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    template = db.get(models.Template, data.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Enforce one proposal per tender+template pair (application-layer uniqueness)
    existing = db.query(models.Proposal).filter(
        models.Proposal.tender_id == data.tender_id,
        models.Proposal.template_id == data.template_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A proposal for this tender and template already exists")

    from backend.document.generator import generate_proposal_file
    try:
        file_path = generate_proposal_file(tender=tender, template=template)
    except OSError:
        raise HTTPException(status_code=507, detail="Insufficient storage. Free up space on the data volume.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proposal generation failed: {str(e)}")

    proposal = models.Proposal(
        tender_id=data.tender_id, template_id=data.template_id,
        file_path=file_path, status="draft",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal_to_out(proposal)


@router.put("/{proposal_id}", response_model=ProposalOut)
def update_proposal(proposal_id: int, data: ProposalUpdate, db: Session = Depends(get_db)):
    proposal = db.get(models.Proposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    proposal.status = data.status
    db.commit()
    db.refresh(proposal)
    return proposal_to_out(proposal)


@router.delete("/{proposal_id}", status_code=204)
def delete_proposal(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.get(models.Proposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if os.path.exists(proposal.file_path):
        os.remove(proposal.file_path)
    db.delete(proposal)
    db.commit()


@router.get("/{proposal_id}/download")
def download_proposal(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.get(models.Proposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if not os.path.exists(proposal.file_path):
        raise HTTPException(status_code=404, detail="Proposal file not found on disk")
    filename = os.path.basename(proposal.file_path)
    return FileResponse(proposal.file_path, filename=filename)
