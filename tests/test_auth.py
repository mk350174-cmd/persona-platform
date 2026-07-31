def test_register_returns_token(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "testpass123"})
    assert r.status_code == 201
    assert "access_token" in r.json()


def test_register_duplicate_email_conflicts(client):
    client.post("/auth/register", json={"email": "dup@example.com", "password": "testpass123"})
    r = client.post("/auth/register", json={"email": "dup@example.com", "password": "testpass123"})
    assert r.status_code == 409


def test_register_short_password_rejected(client):
    r = client.post("/auth/register", json={"email": "b@example.com", "password": "short"})
    assert r.status_code == 422


def test_login_success(client):
    client.post("/auth/register", json={"email": "c@example.com", "password": "testpass123"})
    r = client.post("/auth/login", json={"email": "c@example.com", "password": "testpass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_rejected(client):
    client.post("/auth/register", json={"email": "d@example.com", "password": "testpass123"})
    r = client.post("/auth/login", json={"email": "d@example.com", "password": "WRONG"})
    assert r.status_code == 401


def test_login_unknown_email_rejected(client):
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "testpass123"})
    assert r.status_code == 401


def test_me_requires_bearer_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_rejects_garbage_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "fixture@example.com"
