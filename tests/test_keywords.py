# tests/test_keywords.py

def test_create_keyword(client):
    resp = client.post("/api/keywords", json={"value": "networking", "active": True})
    assert resp.status_code == 201
    assert resp.json()["value"] == "networking"

def test_list_keywords(client):
    client.post("/api/keywords", json={"value": "cloud"})
    client.post("/api/keywords", json={"value": "cybersecurity"})
    resp = client.get("/api/keywords")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2

def test_toggle_keyword_active(client):
    resp = client.post("/api/keywords", json={"value": "firewall", "active": True})
    kw_id = resp.json()["id"]
    resp = client.put(f"/api/keywords/{kw_id}", json={"active": False})
    assert resp.status_code == 200
    assert resp.json()["active"] is False

def test_delete_keyword(client):
    resp = client.post("/api/keywords", json={"value": "vpn"})
    kw_id = resp.json()["id"]
    resp = client.delete(f"/api/keywords/{kw_id}")
    assert resp.status_code == 204
    assert client.get("/api/keywords").json()["total"] == 0

def test_duplicate_keyword_rejected(client):
    client.post("/api/keywords", json={"value": "router"})
    resp = client.post("/api/keywords", json={"value": "router"})
    assert resp.status_code == 409
