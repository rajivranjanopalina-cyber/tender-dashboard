from datetime import datetime

def _create_portal(client):
    resp = client.post("/api/portals", json={"name": "Test Portal", "url": "https://test.gov.in"})
    return resp.json()["id"]

def _create_tender(db_session, portal_id, source_url="https://test.gov.in/t/1", status="new"):
    from backend import models
    tender = models.Tender(
        portal_id=portal_id, title="IT Infrastructure Tender",
        source_url=source_url, matched_keywords='["networking"]',
        status=status, scraped_at=datetime.utcnow(), last_updated_at=datetime.utcnow(),
    )
    db_session.add(tender)
    db_session.commit()
    db_session.refresh(tender)
    return tender

def test_list_tenders_empty(client):
    resp = client.get("/api/tenders")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

def test_list_tenders_filter_by_status(client, db_session):
    portal_id = _create_portal(client)
    _create_tender(db_session, portal_id, "https://t.com/1", "new")
    _create_tender(db_session, portal_id, "https://t.com/2", "approved")
    resp = client.get("/api/tenders?status=new")
    assert resp.json()["total"] == 1

def test_list_tenders_filter_by_keyword(client, db_session):
    portal_id = _create_portal(client)
    _create_tender(db_session, portal_id, "https://t.com/3")
    resp = client.get("/api/tenders?keyword=networking")
    assert resp.json()["total"] == 1
    resp = client.get("/api/tenders?keyword=firewall")
    assert resp.json()["total"] == 0

def test_get_tender_transitions_new_to_under_review(client, db_session):
    portal_id = _create_portal(client)
    tender = _create_tender(db_session, portal_id, "https://t.com/4", "new")
    resp = client.get(f"/api/tenders/{tender.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "under_review"

def test_get_tender_no_transition_if_not_new(client, db_session):
    portal_id = _create_portal(client)
    tender = _create_tender(db_session, portal_id, "https://t.com/5", "approved")
    resp = client.get(f"/api/tenders/{tender.id}")
    assert resp.json()["status"] == "approved"

def test_update_tender_status(client, db_session):
    portal_id = _create_portal(client)
    tender = _create_tender(db_session, portal_id, "https://t.com/6")
    resp = client.put(f"/api/tenders/{tender.id}", json={"status": "approved"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

def test_update_tender_notes(client, db_session):
    portal_id = _create_portal(client)
    tender = _create_tender(db_session, portal_id, "https://t.com/7")
    resp = client.put(f"/api/tenders/{tender.id}", json={"notes": "Worth pursuing"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Worth pursuing"

def test_delete_tender_no_proposals(client, db_session):
    portal_id = _create_portal(client)
    tender = _create_tender(db_session, portal_id, "https://t.com/8")
    resp = client.delete(f"/api/tenders/{tender.id}")
    assert resp.status_code == 204

def test_list_tenders_filter_keyword_case_insensitive(client, db_session):
    from backend import models
    portal_id = _create_portal(client)
    # Store tender with mixed-case keyword
    tender = models.Tender(
        portal_id=portal_id, title="Network Tender",
        source_url="https://t.com/ci1",
        matched_keywords='["Networking"]',  # capital N
        status="new", scraped_at=datetime.utcnow(), last_updated_at=datetime.utcnow(),
    )
    db_session.add(tender)
    db_session.commit()
    # Query with lowercase — should still match
    resp = client.get("/api/tenders?keyword=networking")
    assert resp.json()["total"] == 1
    # Query with uppercase — should also match
    resp = client.get("/api/tenders?keyword=NETWORKING")
    assert resp.json()["total"] == 1

def test_delete_tender_with_proposals_blocked(client, db_session):
    from backend import models
    portal_id = _create_portal(client)
    tender = _create_tender(db_session, portal_id, "https://t.com/9")
    template = models.Template(
        name="T", original_filename="t.docx", file_path="/tmp/t.docx",
        file_type="docx", sha256="abc", is_default=False,
    )
    db_session.add(template)
    db_session.commit()
    proposal = models.Proposal(
        tender_id=tender.id, template_id=template.id,
        file_path="/tmp/p.pdf", status="draft",
    )
    db_session.add(proposal)
    db_session.commit()
    resp = client.delete(f"/api/tenders/{tender.id}")
    assert resp.status_code == 409
