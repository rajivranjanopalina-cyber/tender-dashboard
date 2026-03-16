import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from backend import models
from backend.scraper.engine import scrape_portal

SCRAPE_CONFIG = json.dumps({
    "render_js": False,
    "list_selector": "tr.item",
    "fields": {"title": "td.title", "source_url": "td.url a@href"},
    "pagination": {"type": "none"},
})

SAMPLE_HTML = """
<html><body>
  <table><tr class="item">
    <td class="title">Networking Equipment</td>
    <td class="url"><a href="/t/1">link</a></td>
  </tr></table>
</body></html>
"""

def _make_portal(db_session, requires_auth=False):
    portal = models.Portal(
        name="Test Portal", url="https://test.gov.in",
        enabled=True, requires_auth=requires_auth,
        scrape_config=SCRAPE_CONFIG,
    )
    db_session.add(portal)
    db_session.commit()
    db_session.refresh(portal)
    return portal

def _make_keyword(db_session, value="networking"):
    kw = models.Keyword(value=value, active=True)
    db_session.add(kw)
    db_session.commit()
    return kw

def test_scrape_portal_inserts_matching_tender(db_session):
    portal = _make_portal(db_session)
    _make_keyword(db_session, "networking")
    with patch("backend.scraper.engine.fetch_html", return_value=SAMPLE_HTML):
        result = scrape_portal(portal_id=portal.id, db=db_session)
    assert result["tenders_new"] == 1
    assert result["status"] == "success"
    tender = db_session.query(models.Tender).first()
    assert tender.title == "Networking Equipment"
    assert tender.status == "new"

def test_scrape_portal_skips_non_matching_tender(db_session):
    portal = _make_portal(db_session)
    _make_keyword(db_session, "cybersecurity")  # won't match "Networking"
    with patch("backend.scraper.engine.fetch_html", return_value=SAMPLE_HTML):
        result = scrape_portal(portal_id=portal.id, db=db_session)
    assert result["tenders_new"] == 0
    assert db_session.query(models.Tender).count() == 0

def test_scrape_portal_updates_existing_tender(db_session):
    portal = _make_portal(db_session)
    _make_keyword(db_session, "networking")
    existing = models.Tender(
        portal_id=portal.id, title="Old Title",
        source_url="https://test.gov.in/t/1",
        matched_keywords='["networking"]', status="under_review",
        scraped_at=datetime.utcnow(), last_updated_at=datetime.utcnow(),
    )
    db_session.add(existing)
    db_session.commit()
    with patch("backend.scraper.engine.fetch_html", return_value=SAMPLE_HTML):
        result = scrape_portal(portal_id=portal.id, db=db_session)
    assert result["tenders_new"] == 0
    db_session.refresh(existing)
    assert existing.title == "Networking Equipment"  # updated
    assert existing.status == "under_review"  # not overwritten

def test_scrape_portal_logs_auth_error(db_session):
    portal = _make_portal(db_session, requires_auth=True)  # no credentials set
    result = scrape_portal(portal_id=portal.id, db=db_session)
    assert result["status"] == "failed"
    assert "Auth required" in result["error_message"]

def test_scrape_portal_logs_fetch_error(db_session):
    portal = _make_portal(db_session)
    with patch("backend.scraper.engine.fetch_html", side_effect=Exception("Connection refused")):
        result = scrape_portal(portal_id=portal.id, db=db_session)
    assert result["status"] == "failed"
    assert "Connection refused" in result["error_message"]
