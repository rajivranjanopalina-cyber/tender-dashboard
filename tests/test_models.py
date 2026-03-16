# tests/test_models.py
from contextlib import contextmanager
from datetime import datetime
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend import models

@contextmanager
def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()

def test_portal_model():
    with make_session() as db:
        portal = models.Portal(name="Test Portal", url="https://example.com", enabled=True, requires_auth=False)
        db.add(portal)
        db.commit()
        db.refresh(portal)
        assert portal.id is not None
        assert portal.enabled is True

def test_keyword_model():
    with make_session() as db:
        kw = models.Keyword(value="networking", active=True)
        db.add(kw)
        db.commit()
        assert kw.id is not None

def test_tender_model():
    with make_session() as db:
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
    with make_session() as db:
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
    with make_session() as db:
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
    with make_session() as db:
        portal = models.Portal(name="P", url="http://p.com", enabled=True, requires_auth=False)
        db.add(portal)
        db.commit()
        log = models.ScrapeLog(
            portal_id=portal.id, tenders_found=5, tenders_new=2, status="success"
        )
        db.add(log)
        db.commit()
        assert log.id is not None

def test_keyword_value_unique():
    from sqlalchemy.exc import IntegrityError
    with make_session() as db:
        db.add(models.Keyword(value="networking", active=True))
        db.commit()
        db.add(models.Keyword(value="networking", active=True))
        try:
            db.commit()
            pytest.fail("Expected IntegrityError for duplicate keyword value")
        except IntegrityError:
            db.rollback()

def test_tender_source_url_unique():
    from sqlalchemy.exc import IntegrityError
    with make_session() as db:
        portal = models.Portal(name="P", url="http://p.com", enabled=True, requires_auth=False)
        db.add(portal)
        db.commit()
        db.add(models.Tender(
            portal_id=portal.id, title="T1", source_url="http://p.com/tender/1",
            matched_keywords="[]", status="new",
            scraped_at=datetime(2026, 3, 16), last_updated_at=datetime(2026, 3, 16),
        ))
        db.commit()
        db.add(models.Tender(
            portal_id=portal.id, title="T2", source_url="http://p.com/tender/1",
            matched_keywords="[]", status="new",
            scraped_at=datetime(2026, 3, 16), last_updated_at=datetime(2026, 3, 16),
        ))
        try:
            db.commit()
            pytest.fail("Expected IntegrityError for duplicate source_url")
        except IntegrityError:
            db.rollback()
