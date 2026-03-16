from datetime import datetime
from backend import models

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
        name="Standard", original_filename="s.docx", file_path="/tmp/s.docx",
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
    monkeypatch.setattr("backend.document.generator.generate_proposal_file", lambda *a, **kw: str(tmp_path / "p.docx"))
    tender, template = _setup(db_session)
    resp = client.post("/api/proposals", json={"tender_id": tender.id, "template_id": template.id})
    assert resp.status_code == 201
    proposal_id = resp.json()["id"]
    resp = client.put(f"/api/proposals/{proposal_id}", json={"status": "submitted"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"

def test_duplicate_proposal_rejected(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr("backend.document.generator.generate_proposal_file", lambda *a, **kw: str(tmp_path / "p.docx"))
    tender, template = _setup(db_session)
    client.post("/api/proposals", json={"tender_id": tender.id, "template_id": template.id})
    resp = client.post("/api/proposals", json={"tender_id": tender.id, "template_id": template.id})
    assert resp.status_code == 409

def test_delete_proposal(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    proposal_file = tmp_path / "p.docx"
    proposal_file.write_bytes(b"proposal content")  # create actual file
    monkeypatch.setattr("backend.document.generator.generate_proposal_file", lambda *a, **kw: str(proposal_file))
    tender, template = _setup(db_session)
    resp = client.post("/api/proposals", json={"tender_id": tender.id, "template_id": template.id})
    proposal_id = resp.json()["id"]
    resp = client.delete(f"/api/proposals/{proposal_id}")
    assert resp.status_code == 204
    assert not proposal_file.exists()  # file was deleted from disk
