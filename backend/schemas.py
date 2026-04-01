from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Portals ──────────────────────────────────────────────────────────────────

class PortalCreate(BaseModel):
    name: str
    url: str
    enabled: bool = True
    requires_auth: bool = False
    username: Optional[str] = None
    password: Optional[str] = None  # plaintext on create/update; encrypted before storage
    scrape_config: Optional[str] = None  # JSON string

class PortalUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    enabled: Optional[bool] = None
    requires_auth: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None
    scrape_config: Optional[str] = None

class PortalOut(BaseModel):
    id: int
    name: str
    url: str
    enabled: bool
    requires_auth: bool
    username: Optional[str]
    last_scraped_at: Optional[datetime]
    scrape_config: Optional[str]
    created_at: datetime
    has_password: bool  # True if password_enc is set; never return the encrypted value

    model_config = {"from_attributes": True}


# ── Keywords ─────────────────────────────────────────────────────────────────

class KeywordCreate(BaseModel):
    value: str
    active: bool = True

class KeywordUpdate(BaseModel):
    value: Optional[str] = None
    active: Optional[bool] = None

class KeywordOut(BaseModel):
    id: int
    value: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Tenders ──────────────────────────────────────────────────────────────────

class TenderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class TenderOut(BaseModel):
    id: int
    portal_id: int
    portal_name: str
    title: str
    description: Optional[str]
    published_date: Optional[str]
    deadline: Optional[str]
    estimated_value: Optional[str]
    source_url: str
    matched_keywords: str  # JSON string
    status: str
    notes: Optional[str]
    scraped_at: datetime
    last_updated_at: datetime

    model_config = {"from_attributes": True}


# ── Templates ─────────────────────────────────────────────────────────────────

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None

class TemplateOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    original_filename: str
    file_type: str
    sha256: str
    is_default: bool
    blob_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Proposals ────────────────────────────────────────────────────────────────

class ProposalCreate(BaseModel):
    tender_id: int
    template_id: int

class ProposalUpdate(BaseModel):
    status: str

class ProposalOut(BaseModel):
    id: int
    tender_id: int
    tender_title: str
    template_id: Optional[int]
    template_name: Optional[str]
    blob_url: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Scraper ──────────────────────────────────────────────────────────────────

class ScrapeRunRequest(BaseModel):
    portal_id: Optional[int] = None

class ScrapeLogOut(BaseModel):
    id: int
    portal_id: int
    portal_name: str
    run_at: datetime
    tenders_found: int
    tenders_new: int
    status: str
    error_message: Optional[str]

    model_config = {"from_attributes": True}

class ScraperStatusOut(BaseModel):
    is_running: bool
    next_run_at: Optional[datetime]


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


# ── Errors ────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: str
