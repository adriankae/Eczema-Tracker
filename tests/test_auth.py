from __future__ import annotations


def test_login_and_me(client):
    response = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["account"]["username"] == "admin"

    token = data["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_api_key_auth(client):
    login = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    token = login.json()["access_token"]
    created = client.post("/api-keys", headers={"Authorization": f"Bearer {token}"}, json={"name": "cli"})
    assert created.status_code == 200
    plaintext = created.json()["plaintext_key"]

    me = client.get("/auth/me", headers={"X-API-Key": plaintext})
    assert me.status_code == 200
