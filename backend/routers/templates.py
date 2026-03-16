import hashlib
import os
import shutil
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models
from backend.schemas import TemplateOut, TemplateUpdate, PaginatedResponse

router = APIRouter()


def _templates_dir() -> str:
    """Resolve lazily — read DATA_DIR from env directly so test monkeypatching works."""
    d = os.path.join(os.environ.get("DATA_DIR", "/data"), "templates")
    os.makedirs(d, exist_ok=True)
    return d


def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    if ext not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    content = await file.read()
    sha = _sha256_of_bytes(content)

    # Validate PDF has AcroForm fields
    if ext == "pdf":
        from backend.document.pdf_handler import NoAcroFormFieldsError, validate_pdf_acroform_fields
        try:
            validate_pdf_acroform_fields(content)
        except NoAcroFormFieldsError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            raise HTTPException(status_code=400, detail="Could not read PDF file.")

    save_path = os.path.join(_templates_dir(), f"{sha}.{ext}")
    try:
        with open(save_path, "wb") as f:
            f.write(content)
    except OSError:
        raise HTTPException(status_code=507, detail="Insufficient storage. Free up space on the data volume.")

    if is_default:
        db.query(models.Template).filter(models.Template.is_default == True).update({"is_default": False})

    template = models.Template(
        name=name, description=description, original_filename=filename,
        file_path=save_path, file_type=ext, sha256=sha, is_default=is_default,
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

    # Delete file from disk
    if os.path.exists(template.file_path):
        os.remove(template.file_path)

    db.delete(template)
    db.commit()


@router.get("/{template_id}/download")
def download_template(template_id: int, db: Session = Depends(get_db)):
    template = db.get(models.Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not os.path.exists(template.file_path):
        raise HTTPException(status_code=404, detail="Template file not found on disk")
    return FileResponse(template.file_path, filename=template.original_filename)
