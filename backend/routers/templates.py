import hashlib
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models
from backend.schemas import TemplateOut, TemplateUpdate, PaginatedResponse
from backend.blob_storage import upload_blob, download_blob, delete_blob

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
def list_templates(page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    page_size = min(page_size, 200)
    total = db.query(models.Template).count()
    items = db.query(models.Template).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[TemplateOut.model_validate(t).model_dump() for t in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=TemplateOut, status_code=201)
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
    is_default: bool = Form(False),
    db: Session = Depends(get_db),
):
    filename = file.filename or "template"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("docx",):
        raise HTTPException(status_code=400, detail="Only DOCX files are supported")

    content = await file.read()
    sha_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = db.query(models.Template).filter(models.Template.sha256 == sha_hash).first()
    if existing:
        raise HTTPException(status_code=409, detail="Template already uploaded")

    blob_url = upload_blob(content, f"templates/{sha_hash}_{filename}")

    if is_default:
        db.query(models.Template).filter(models.Template.is_default == True).update({"is_default": False})

    template = models.Template(
        name=name,
        description=description,
        original_filename=filename,
        blob_url=blob_url,
        file_type="docx",
        sha256=sha_hash,
        is_default=is_default,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return TemplateOut.model_validate(template)


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(template_id: int, data: TemplateUpdate, db: Session = Depends(get_db)):
    template = db.get(models.Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if data.name is not None:
        template.name = data.name
    if data.description is not None:
        template.description = data.description
    if data.is_default is not None:
        if data.is_default:
            db.query(models.Template).filter(models.Template.id != template_id, models.Template.is_default == True).update({"is_default": False})
        template.is_default = data.is_default
    db.commit()
    db.refresh(template)
    return TemplateOut.model_validate(template)


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.get(models.Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    active_proposals = db.query(models.Proposal).filter(
        models.Proposal.template_id == template_id,
        models.Proposal.status.in_(["draft", "submitted"]),
    ).count()
    if active_proposals > 0:
        raise HTTPException(status_code=409, detail="Cannot delete template with active proposals (draft or submitted)")

    # Nullify template_id on completed proposals
    db.query(models.Proposal).filter(
        models.Proposal.template_id == template_id,
        models.Proposal.status.in_(["won", "lost"]),
    ).update({"template_id": None})

    # Delete from Vercel Blob
    try:
        delete_blob(template.blob_url)
    except Exception:
        pass  # Best-effort: don't block DB delete if blob deletion fails

    db.delete(template)
    db.commit()


@router.get("/{template_id}/download")
def download_template(template_id: int, db: Session = Depends(get_db)):
    template = db.get(models.Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    try:
        content = download_blob(template.blob_url)
    except Exception:
        raise HTTPException(status_code=404, detail="Template file not found in storage")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{template.original_filename}"'},
    )
