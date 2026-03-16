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

def test_update_keyword_duplicate_value_rejected(client):
    client.post("/api/keywords", json={"value": "alpha"})
    resp = client.post("/api/keywords", json={"value": "beta"})
    beta_id = resp.json()["id"]
    resp = client.put(f"/api/keywords/{beta_id}", json={"value": "alpha"})
    assert resp.status_code == 409

def test_update_nonexistent_keyword(client):
    resp = client.put("/api/keywords/999", json={"active": False})
    assert resp.status_code == 404

def test_delete_nonexistent_keyword(client):
    resp = client.delete("/api/keywords/999")
    assert resp.status_code == 404
