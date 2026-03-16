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
