import os
import subprocess
from datetime import date
from backend import models


def _proposals_dir() -> str:
    """Resolve lazily so DATA_DIR monkeypatching in tests works correctly."""
    data_dir = os.environ.get("DATA_DIR", "/data")
    d = os.path.join(data_dir, "proposals")
    os.makedirs(d, exist_ok=True)
    return d


PLACEHOLDER_MAP = {
    "tender_title": lambda t, p: t.title or "",
    "tender_description": lambda t, p: t.description or "",
    "tender_deadline": lambda t, p: t.deadline or "",
    "tender_published_date": lambda t, p: t.published_date or "",
    "tender_estimated_value": lambda t, p: t.estimated_value or "",
    "tender_source_url": lambda t, p: t.source_url or "",
    "tender_portal_name": lambda t, p: p.name if p else "",
    "tender_portal_url": lambda t, p: p.url if p else "",
    "generation_date": lambda t, p: str(date.today()),
}


def _build_placeholders(tender: models.Tender) -> dict[str, str]:
    portal = tender.portal
    return {key: fn(tender, portal) for key, fn in PLACEHOLDER_MAP.items()}


def generate_proposal_file(tender: models.Tender, template: models.Template) -> str:
    """
    Generate a proposal file from a tender and template.
    Returns the path to the generated file.
    Raises OSError on disk full; other exceptions on generation failure.
    """
    placeholders = _build_placeholders(tender)

    with open(template.file_path, "rb") as f:
        template_bytes = f.read()

    base_name = f"proposal_{tender.id}_{template.id}"

    if template.file_type == "docx":
        from backend.document.docx_handler import fill_docx_template
        out_path = os.path.join(_proposals_dir(), f"{base_name}.docx")
        fill_docx_template(template_bytes, placeholders, out_path)

    elif template.file_type == "pdf":
        from backend.document.pdf_handler import fill_pdf_template
        out_path = os.path.join(_proposals_dir(), f"{base_name}.pdf")
        fill_pdf_template(template_bytes, placeholders, out_path)

    else:
        raise ValueError(f"Unsupported template type: {template.file_type}")

    return out_path


def convert_docx_to_pdf(docx_path: str) -> str | None:
    """
    Convert a DOCX file to PDF using LibreOffice headless.
    Returns the PDF path on success, or None if LibreOffice is unavailable.
    """
    out_dir = os.path.dirname(docx_path)
    try:
        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", out_dir, docx_path],
            capture_output=True, timeout=60,
        )
        if result.returncode == 0:
            pdf_path = docx_path.replace(".docx", ".pdf")
            if os.path.exists(pdf_path):
                return pdf_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None
