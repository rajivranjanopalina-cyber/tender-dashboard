import os
from datetime import date
from backend import models
from backend.blob_storage import download_blob, upload_blob


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
    "company_name": lambda t, p: os.environ.get("COMPANY_NAME", ""),
    "company_address": lambda t, p: os.environ.get("COMPANY_ADDRESS", ""),
    "company_contact": lambda t, p: os.environ.get("COMPANY_CONTACT", ""),
}


def _build_placeholders(tender: models.Tender) -> dict[str, str]:
    portal = tender.portal
    return {key: fn(tender, portal) for key, fn in PLACEHOLDER_MAP.items()}


def generate_proposal(tender: models.Tender, template: models.Template) -> str:
    """
    Generate a proposal DOCX from a tender and template.
    Downloads template from Blob, fills placeholders, uploads result to Blob.
    Returns the blob_url of the generated proposal.
    """
    placeholders = _build_placeholders(tender)

    # Download template from Vercel Blob
    template_bytes = download_blob(template.blob_url)

    # Generate DOCX
    from backend.document.docx_handler import fill_docx_template
    output_bytes = fill_docx_template(template_bytes, placeholders)

    # Upload generated proposal to Blob
    filename = f"proposals/proposal_{tender.id}_{template.id}.docx"
    blob_url = upload_blob(output_bytes, filename)

    return blob_url
