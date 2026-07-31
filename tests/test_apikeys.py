def test_create_api_key_requires_auth(client):
    r = client.post("/apikeys/")
    assert r.status_code == 401


def test_create_api_key_returns_raw_key_once(client, auth_headers):
    r = client.post("/apikeys/", headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["api_key"].startswith("prs_")
    assert body["key_preview"] in body["api_key"] or body["key_preview"].startswith(body["api_key"][:8])


def test_list_api_keys_never_returns_raw_key(client, auth_headers):
    client.post("/apikeys/", headers=auth_headers)
    r = client.get("/apikeys/", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert "api_key" not in body[0]
    assert body[0]["revoked"] is False


def test_revoke_api_key(client, auth_headers):
    created = client.post("/apikeys/", headers=auth_headers).json()
    r = client.delete(f"/apikeys/{created['id']}", headers=auth_headers)
    assert r.status_code == 204
    listing = client.get("/apikeys/", headers=auth_headers).json()
    assert listing[0]["revoked"] is True


def test_revoke_unknown_key_404s(client, auth_headers):
    r = client.delete("/apikeys/99999", headers=auth_headers)
    assert r.status_code == 404


def test_cannot_revoke_another_users_key(client, auth_headers):
    client.post("/auth/register", json={"email": "other@example.com", "password": "testpass123", "date_of_birth": "1990-01-01"})
    other_login = client.post("/auth/login", json={"email": "other@example.com", "password": "testpass123", "date_of_birth": "1990-01-01"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    created = client.post("/apikeys/", headers=auth_headers).json()
    r = client.delete(f"/apikeys/{created['id']}", headers=other_headers)
    assert r.status_code == 404
