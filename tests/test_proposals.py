from datetime import datetime
from unittest.mock import patch
from backend import models

FAKE_BLOB_URL = "https://blob.vercel-storage.com/proposals/p.docx"
FAKE_TEMPLATE_BLOB_URL = "https://blob.vercel-storage.com/templates/s.docx"


def _setup(db_session):
    portal = models.Portal(name="P", url="http://p.com", enabled=True, requires_auth=False)
    db_session.add(portal)
    db_session.commit()
    tender = models.Tender(
        portal_id=portal.id, title="IT Tender", source_url="http://p.com/t/1",
        matched_keywords='["networking"]', status="approved",
        scraped_at=datetime.utcnow(), last_updated_at=datetime.utcnow(),
    )
    template = models.Template(
        name="Standard", original_filename="s.docx", blob_url=FAKE_TEMPLATE_BLOB_URL,
        file_type="docx", sha256="abc", is_default=True,
    )
    db_session.add_all([tender, template])
    db_session.commit()
    return tender, template


def test_list_proposals_empty(client):
    resp = client.get("/api/proposals")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_update_proposal_status(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    tender, template = _setup(db_session)
    with patch("backend.routers.proposals.generate_proposal", return_value=FAKE_BLOB_URL):
        resp = client.post("/api/proposals", json={"tender_id": tender.id, "template_id": template.id})
    assert resp.status_code == 201
    proposal_id = resp.json()["id"]
    resp = client.put(f"/api/proposals/{proposal_id}", json={"status": "submitted"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


def test_duplicate_proposal_rejected(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    tender, template = _setup(db_session)
    with patch("backend.routers.proposals.generate_proposal", return_value=FAKE_BLOB_URL):
        client.post("/api/proposals", json={"tender_id": tender.id, "template_id": template.id})
        resp = client.post("/api/proposals", json={"tender_id": tender.id, "template_id": template.id})
    assert resp.status_code == 409


def test_delete_proposal(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    tender, template = _setup(db_session)
    with patch("backend.routers.proposals.generate_proposal", return_value=FAKE_BLOB_URL):
        resp = client.post("/api/proposals", json={"tender_id": tender.id, "template_id": template.id})
    proposal_id = resp.json()["id"]
    with patch("backend.routers.proposals.delete_blob", return_value=None):
        resp = client.delete(f"/api/proposals/{proposal_id}")
    assert resp.status_code == 204
