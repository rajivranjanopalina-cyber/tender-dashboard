# tests/test_models.py
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend import models

def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()

def test_portal_model():
    db = make_session()
    portal = models.Portal(name="Test Portal", url="https://example.com", enabled=True, requires_auth=False)
    db.add(portal)
    db.commit()
    db.refresh(portal)
    assert portal.id is not None
    assert portal.enabled is True

def test_keyword_model():
    db = make_session()
    kw = models.Keyword(value="networking", active=True)
    db.add(kw)
    db.commit()
    assert kw.id is not None

def test_tender_model():
    db = make_session()
    portal = models.Portal(name="P", url="http://p.com", enabled=True, requires_auth=False)
    db.add(portal)
    db.commit()
    tender = models.Tender(
        portal_id=portal.id,
        title="Test Tender",
        source_url="http://p.com/t/1",
        matched_keywords='["networking"]',
        status="new",
        scraped_at=datetime(2026, 3, 16),
        last_updated_at=datetime(2026, 3, 16),
    )
    db.add(tender)
    db.commit()
    assert tender.id is not None
    assert tender.status == "new"

def test_template_model():
    db = make_session()
    t = models.Template(
        name="Standard Proposal",
        original_filename="proposal.docx",
        file_path="/data/templates/proposal.docx",
        file_type="docx",
        sha256="abc123",
        is_default=True,
    )
    db.add(t)
    db.commit()
    assert t.id is not None

def test_proposal_model():
    db = make_session()
    portal = models.Portal(name="P", url="http://p.com", enabled=True, requires_auth=False)
    db.add(portal)
    db.commit()
    tender = models.Tender(
        portal_id=portal.id, title="T", source_url="http://p.com/t/2",
        matched_keywords="[]", status="approved",
        scraped_at=datetime(2026, 3, 16), last_updated_at=datetime(2026, 3, 16),
    )
    template = models.Template(
        name="T", original_filename="t.docx", file_path="/data/t.docx",
        file_type="docx", sha256="xyz", is_default=False,
    )
    db.add_all([tender, template])
    db.commit()
    proposal = models.Proposal(
        tender_id=tender.id, template_id=template.id,
        file_path="/data/proposals/p.pdf", status="draft",
    )
    db.add(proposal)
    db.commit()
    assert proposal.id is not None

def test_scrape_log_model():
    db = make_session()
    portal = models.Portal(name="P", url="http://p.com", enabled=True, requires_auth=False)
    db.add(portal)
    db.commit()
    log = models.ScrapeLog(
        portal_id=portal.id, tenders_found=5, tenders_new=2, status="success"
    )
    db.add(log)
    db.commit()
    assert log.id is not None
