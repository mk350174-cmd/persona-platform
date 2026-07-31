def test_register_rejects_underage(client):
    r = client.post("/auth/register", json={
        "email": "kid@example.com", "password": "testpass123",
        "date_of_birth": "2015-01-01",
    })
    assert r.status_code == 422


def test_register_rejects_future_date_of_birth(client):
    r = client.post("/auth/register", json={
        "email": "timetraveler@example.com", "password": "testpass123",
        "date_of_birth": "2099-01-01",
    })
    assert r.status_code == 422


def test_register_accepts_exactly_18(client):
    from datetime import date
    today = date.today()
    dob = today.replace(year=today.year - 18)
    r = client.post("/auth/register", json={
        "email": "just18@example.com", "password": "testpass123",
        "date_of_birth": dob.isoformat(),
    })
    assert r.status_code == 201


def test_register_missing_date_of_birth_rejected(client):
    r = client.post("/auth/register", json={"email": "nodobs@example.com", "password": "testpass123"})
    assert r.status_code == 422


def test_data_export_requires_auth(client):
    r = client.get("/privacy/data-export")
    assert r.status_code == 401


def test_data_export_reflects_user_data(client, auth_headers):
    client.post("/apikeys/", headers=auth_headers)
    r = client.get("/privacy/data-export", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "fixture@example.com"
    assert body["date_of_birth"] == "1990-01-01"
    assert len(body["api_keys"]) == 1
    assert body["purchases"] == []
    assert body["chat_messages"] == []


def test_delete_account_requires_auth(client):
    r = client.delete("/privacy/account")
    assert r.status_code == 401


def test_delete_account_removes_user_and_data(client, auth_headers):
    client.post("/apikeys/", headers=auth_headers)
    r = client.delete("/privacy/account", headers=auth_headers)
    assert r.status_code == 204

    # Old token should no longer resolve to a user.
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 401


def test_delete_account_allows_re_registration_with_same_email(client, auth_headers):
    client.delete("/privacy/account", headers=auth_headers)
    r = client.post("/auth/register", json={
        "email": "fixture@example.com", "password": "testpass123",
        "date_of_birth": "1990-01-01",
    })
    assert r.status_code == 201
