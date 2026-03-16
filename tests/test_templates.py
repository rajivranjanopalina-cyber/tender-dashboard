import io
import os

def _make_fake_docx():
    return io.BytesIO(b"fake docx content for testing")

def test_upload_template_docx(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    content = io.BytesIO(b"fake docx content")
    resp = client.post(
        "/api/templates",
        data={"name": "Standard Proposal", "description": "Default template", "is_default": "true"},
        files={"file": ("proposal.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Standard Proposal"
    assert data["file_type"] == "docx"
    assert data["original_filename"] == "proposal.docx"
    assert "sha256" in data

def test_list_templates(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    content = io.BytesIO(b"fake docx")
    client.post(
        "/api/templates",
        data={"name": "T1"},
        files={"file": ("t1.docx", content, "application/octet-stream")},
    )
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

def test_update_template_metadata(client, tmp_path, monkeypatch, db_session):
    from backend import models
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    t = models.Template(
        name="Old Name", original_filename="t.docx",
        file_path=str(tmp_path / "t.docx"), file_type="docx", sha256="abc", is_default=False,
    )
    db_session.add(t)
    db_session.commit()
    resp = client.put(f"/api/templates/{t.id}", json={"name": "New Name", "is_default": True})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["is_default"] is True

def test_delete_template_no_active_proposals(client, tmp_path, monkeypatch, db_session):
    from backend import models
    file = tmp_path / "t.docx"
    file.write_bytes(b"content")
    t = models.Template(
        name="T", original_filename="t.docx", file_path=str(file),
        file_type="docx", sha256="abc", is_default=False,
    )
    db_session.add(t)
    db_session.commit()
    resp = client.delete(f"/api/templates/{t.id}")
    assert resp.status_code == 204
    assert not file.exists()

def test_delete_template_with_active_proposal_blocked(client, db_session, tmp_path):
    from backend import models
    from datetime import datetime
    portal = models.Portal(name="P", url="http://p.com", enabled=True, requires_auth=False)
    db_session.add(portal)
    db_session.commit()
    tender = models.Tender(
        portal_id=portal.id, title="T", source_url="http://p.com/t/1",
        matched_keywords="[]", status="approved",
        scraped_at=datetime.utcnow(), last_updated_at=datetime.utcnow(),
    )
    t = models.Template(
        name="T", original_filename="t.docx",
        file_path=str(tmp_path / "t.docx"), file_type="docx", sha256="abc", is_default=False,
    )
    db_session.add_all([tender, t])
    db_session.commit()
    proposal = models.Proposal(
        tender_id=tender.id, template_id=t.id, file_path="/tmp/p.pdf", status="draft",
    )
    db_session.add(proposal)
    db_session.commit()
    resp = client.delete(f"/api/templates/{t.id}")
    assert resp.status_code == 409
