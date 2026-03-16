# tests/test_portals.py

def test_create_portal(client):
    resp = client.post("/api/portals", json={
        "name": "MP Tenders", "url": "https://mptenders.gov.in", "enabled": True, "requires_auth": False
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "MP Tenders"
    assert "has_password" in data
    assert data["has_password"] is False

def test_create_portal_with_password(client):
    resp = client.post("/api/portals", json={
        "name": "Auth Portal", "url": "https://auth.gov.in",
        "requires_auth": True, "username": "user1", "password": "secret123"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["has_password"] is True
    assert "password" not in data  # plaintext never returned
    assert "password_enc" not in data  # encrypted value is never returned

def test_list_portals(client):
    client.post("/api/portals", json={"name": "P1", "url": "https://p1.com"})
    client.post("/api/portals", json={"name": "P2", "url": "https://p2.com"})
    resp = client.get("/api/portals")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2

def test_update_portal_enable_toggle(client):
    resp = client.post("/api/portals", json={"name": "P", "url": "https://p.com", "enabled": True})
    portal_id = resp.json()["id"]
    resp = client.put(f"/api/portals/{portal_id}", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

def test_delete_portal(client):
    resp = client.post("/api/portals", json={"name": "P", "url": "https://p.com"})
    portal_id = resp.json()["id"]
    resp = client.delete(f"/api/portals/{portal_id}")
    assert resp.status_code == 204
    resp = client.get("/api/portals")
    assert resp.json()["total"] == 0

def test_get_nonexistent_portal(client):
    resp = client.get("/api/portals/999")
    assert resp.status_code == 404

def test_delete_portal_cascades(client, db_session):
    # Create portal via API
    resp = client.post("/api/portals", json={"name": "Cascade Test", "url": "https://ct.com"})
    assert resp.status_code == 201
    portal_id = resp.json()["id"]

    # Create a tender linked to this portal directly in DB
    from datetime import datetime
    from backend import models
    tender = models.Tender(
        portal_id=portal_id, title="T1", source_url="https://ct.com/t/1",
        matched_keywords="[]", status="new",
        scraped_at=datetime(2026, 3, 16), last_updated_at=datetime(2026, 3, 16),
    )
    db_session.add(tender)
    db_session.commit()
    tender_id = tender.id

    # Create a proposal linked to that tender
    from backend import models as m
    tmpl = models.Template(
        name="T", original_filename="t.docx", file_path="/data/t.docx",
        file_type="docx", sha256="a" * 64, is_default=False,
    )
    db_session.add(tmpl)
    db_session.commit()
    proposal = models.Proposal(
        tender_id=tender_id, template_id=tmpl.id,
        file_path="/data/proposals/p.pdf", status="draft",
    )
    db_session.add(proposal)
    db_session.commit()
    proposal_id = proposal.id

    # Delete the portal via API
    resp = client.delete(f"/api/portals/{portal_id}")
    assert resp.status_code == 204

    # Verify portal, tender, and proposal are all gone
    db_session.expire_all()
    assert db_session.get(models.Portal, portal_id) is None
    assert db_session.get(models.Tender, tender_id) is None
    assert db_session.get(models.Proposal, proposal_id) is None
