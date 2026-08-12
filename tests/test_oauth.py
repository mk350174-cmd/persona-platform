"""T2-008 tests. No real Google/GitHub credentials in this environment
(GOOGLE_CLIENT_ID etc. are unset), so the /login and /callback routes are
expected to return 503 -- this repo has no real OAuth app registration and
can't have one (see docs/OAUTH2_KURULUM_REHBERI.md). The find-or-create
and date-of-birth-completion logic is tested directly since it doesn't
depend on reaching a real provider."""
from __future__ import annotations

from datetime import date

from api.db import SessionLocal
from api.routers.oauth_router import _find_or_create_user


def test_oauth_login_unconfigured_returns_503(client):
    r = client.get("/auth/google/login", follow_redirects=False)
    assert r.status_code == 503


def test_oauth_login_unknown_provider_404s(client):
    r = client.get("/auth/nobody/login", follow_redirects=False)
    assert r.status_code == 404


def test_oauth_callback_unconfigured_returns_503(client):
    r = client.get("/auth/google/callback?code=x&state=y", follow_redirects=False)
    assert r.status_code == 503


def test_find_or_create_creates_new_oauth_user(client):
    db = SessionLocal()
    try:
        user = _find_or_create_user(db, "google", "g-12345", "newoauth@example.com")
        assert user.oauth_provider == "google"
        assert user.oauth_id == "g-12345"
        assert user.password_hash is None
        assert user.date_of_birth is None
        assert user.email_verified is True
    finally:
        db.close()


def test_find_or_create_is_idempotent(client):
    db = SessionLocal()
    try:
        first = _find_or_create_user(db, "github", "gh-999", "same@example.com")
        second = _find_or_create_user(db, "github", "gh-999", "same@example.com")
        assert first.id == second.id
    finally:
        db.close()


def test_find_or_create_links_existing_password_account(client):
    client.post("/auth/register", json={
        "email": "linkme@example.com", "password": "testpass123",
        "date_of_birth": "1990-01-01",
    })
    db = SessionLocal()
    try:
        linked = _find_or_create_user(db, "google", "g-link-1", "linkme@example.com")
        assert linked.oauth_provider == "google"
        assert linked.password_hash is not None  # original password preserved
        assert linked.date_of_birth == date(1990, 1, 1)  # original DOB preserved
    finally:
        db.close()


def test_oauth_user_cannot_login_with_password(client):
    db = SessionLocal()
    try:
        _find_or_create_user(db, "google", "g-nopass", "nopass@example.com")
    finally:
        db.close()
    r = client.post("/auth/login", json={"email": "nopass@example.com", "password": "anything123"})
    assert r.status_code == 401


def test_date_of_birth_patch_requires_auth(client):
    r = client.patch("/auth/me/date-of-birth", json={"date_of_birth": "1990-01-01"})
    assert r.status_code == 401


def test_date_of_birth_patch_completes_oauth_profile(client):
    from api.security import create_access_token
    db = SessionLocal()
    try:
        user = _find_or_create_user(db, "google", "g-dob-test", "dobtest@example.com")
        assert user.date_of_birth is None
        token = create_access_token(user.id)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/auth/me", headers=headers)
    assert r.json()["date_of_birth"] is None

    r = client.patch("/auth/me/date-of-birth", json={"date_of_birth": "1995-06-15"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["date_of_birth"] == "1995-06-15"

    r = client.get("/auth/me", headers=headers)
    assert r.json()["date_of_birth"] == "1995-06-15"


def test_oauth_login_redirects_when_configured(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "fake-client-secret")
    r = client.get("/auth/google/login", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "accounts.google.com" in r.headers["location"]
    assert "fake-client-id" in r.headers["location"]
    assert "state=" in r.headers["location"]


def test_oauth_callback_full_flow_mocked(client, monkeypatch):
    """Mocks the provider HTTP calls (token exchange + userinfo) end-to-end
    -- this is the code path the 'unconfigured returns 503' tests above
    don't exercise at all."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "fake-client-secret")

    login_resp = client.get("/auth/google/login", follow_redirects=False)
    from urllib.parse import urlparse, parse_qs
    state = parse_qs(urlparse(login_resp.headers["location"]).query)["state"][0]

    class _FakeResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data

        def json(self):
            return self._json

    class _FakeHttpxClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, **kw):
            assert "oauth2.googleapis.com/token" in url
            return _FakeResponse(200, {"access_token": "fake-access-token"})

        def get(self, url, **kw):
            assert "googleapis.com/oauth2/v3/userinfo" in url
            return _FakeResponse(200, {"sub": "google-uid-42", "email": "realuser@example.com"})

    import api.routers.oauth_router as oauth_mod
    monkeypatch.setattr(oauth_mod.httpx, "Client", _FakeHttpxClient)

    r = client.get(f"/auth/google/callback?code=fake-code&state={state}", follow_redirects=False)
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["needs_date_of_birth"] is True

    # The issued token actually works against a real protected endpoint.
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "realuser@example.com"


def test_oauth_callback_rejects_bad_state(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "fake-client-secret")
    r = client.get("/auth/google/callback?code=x&state=not-a-real-jwt", follow_redirects=False)
    assert r.status_code == 400


def test_date_of_birth_patch_rejects_underage(client):
    from api.security import create_access_token
    db = SessionLocal()
    try:
        user = _find_or_create_user(db, "google", "g-underage", "underage@example.com")
        token = create_access_token(user.id)
    finally:
        db.close()

    r = client.patch("/auth/me/date-of-birth", json={"date_of_birth": "2020-01-01"},
                      headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422
