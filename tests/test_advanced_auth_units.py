"""
Unit tests for api/advanced_auth.py — RBAC, JWT, OAuth helpers, sessions.

Pure helpers + JWT round-trips need no network. The async JWT dependency and the
permission/role factories are driven with a fake Request + a seeded `test_db`.
OAuth network calls are exercised via httpx.MockTransport.
"""

import asyncio
from datetime import timedelta

import httpx
import jwt as pyjwt
import pytest
from fastapi import HTTPException

from api.advanced_auth import (
    UserRole,
    has_permission,
    JWTTokenManager,
    get_token_manager,
    GoogleOAuth2,
    GitHubOAuth2,
    get_google_oauth,
    get_github_oauth,
    SessionManager,
    get_session_manager,
    get_current_user_jwt,
    require_permission,
    require_role,
    generate_oauth_state,
    verify_oauth_state,
    generate_secure_password,
    check_password_strength,
)
from api.db import create_user


# ── RBAC ─────────────────────────────────────────────────────────────────────

def test_has_permission_matrix():
    assert has_permission(UserRole.ADMIN, "users:write_all") is True
    assert has_permission(UserRole.USER, "personas:read") is True
    assert has_permission(UserRole.FREE, "users:write_all") is False
    assert has_permission(UserRole.USER, "nonexistent:perm") is False


# ── JWT round-trip ───────────────────────────────────────────────────────────

def test_access_token_roundtrip():
    mgr = JWTTokenManager()
    token = mgr.create_access_token("usr_1", "a@b.com", UserRole.ADMIN)
    payload = mgr.verify_token(token)
    assert payload["sub"] == "usr_1"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip():
    mgr = JWTTokenManager()
    token = mgr.create_refresh_token("usr_1", "a@b.com")
    payload = mgr.verify_token(token)
    assert payload["type"] == "refresh"


def test_verify_expired_token_raises_401():
    mgr = JWTTokenManager()
    token = mgr.create_access_token("u", "a@b.com", expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as ei:
        mgr.verify_token(token)
    assert ei.value.status_code == 401
    assert "expired" in ei.value.detail.lower()


def test_verify_invalid_token_raises_401():
    mgr = JWTTokenManager()
    with pytest.raises(HTTPException) as ei:
        mgr.verify_token("not.a.jwt")
    assert ei.value.status_code == 401


def test_verify_wrong_secret_raises_401():
    mgr = JWTTokenManager()
    forged = pyjwt.encode({"sub": "x"}, "different_secret", algorithm="HS256")
    with pytest.raises(HTTPException):
        mgr.verify_token(forged)


def test_get_token_manager_singleton():
    assert get_token_manager() is get_token_manager()


# ── OAuth URL builders (pure) ────────────────────────────────────────────────

def test_google_authorization_url():
    url = GoogleOAuth2().get_authorization_url("state123")
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "state=state123" in url
    assert "response_type=code" in url


def test_github_authorization_url():
    url = GitHubOAuth2().get_authorization_url("st")
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert "state=st" in url


def test_oauth_singletons():
    assert get_google_oauth() is get_google_oauth()
    assert get_github_oauth() is get_github_oauth()


# ── OAuth network calls (MockTransport) ──────────────────────────────────────

def test_google_exchange_and_userinfo(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if "token" in str(request.url):
            return httpx.Response(200, json={"access_token": "at_1"})
        return httpx.Response(200, json={"email": "g@x.com", "sub": "google_1"})

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def _factory(*a, **k):
        return real_client(transport=transport)

    monkeypatch.setattr(httpx, "AsyncClient", _factory)
    g = GoogleOAuth2()
    tok = asyncio.run(g.exchange_code_for_token("code123"))
    assert tok["access_token"] == "at_1"
    info = asyncio.run(g.get_user_info("at_1"))
    assert info["email"] == "g@x.com"


def test_github_exchange_and_userinfo(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if "access_token" in str(request.url):
            return httpx.Response(200, json={"access_token": "gh_at"})
        return httpx.Response(200, json={"login": "octocat"})

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))
    gh = GitHubOAuth2()
    assert asyncio.run(gh.exchange_code_for_token("c"))["access_token"] == "gh_at"
    assert asyncio.run(gh.get_user_info("gh_at"))["login"] == "octocat"


# ── SessionManager ───────────────────────────────────────────────────────────

def test_session_invalidate_and_check():
    sm = SessionManager()
    assert sm.is_session_valid("tok") is True
    sm.invalidate_session("tok", "usr_1")
    assert sm.is_session_valid("tok") is False
    sm.clear_user_sessions("usr_1")   # no-op, must not raise


def test_get_session_manager_singleton():
    assert get_session_manager() is get_session_manager()


# ── OAuth state ──────────────────────────────────────────────────────────────

def test_generate_and_verify_oauth_state():
    state = generate_oauth_state("usr_1", "google")
    user_id, provider = verify_oauth_state(state)
    assert user_id == "usr_1" and provider == "google"


def test_verify_oauth_state_invalid():
    with pytest.raises(HTTPException) as ei:
        verify_oauth_state("garbage")
    assert ei.value.status_code == 400
    with pytest.raises(HTTPException):
        verify_oauth_state("usr_1:not_a_provider:xyz")


# ── password utilities ───────────────────────────────────────────────────────

def test_generate_secure_password_length():
    assert len(generate_secure_password()) >= 16


def test_check_password_strength():
    ok, msg = check_password_strength("Str0ng!Pass")
    assert ok is True and msg == ""
    bad, msg = check_password_strength("weak")
    assert bad is False
    assert "8 characters" in msg and "uppercase" in msg


# ── async JWT dependency + RBAC factories (test_db) ──────────────────────────

class _FakeRequest:
    def __init__(self, auth):
        self.headers = {"Authorization": auth} if auth else {}
        # mimic Starlette Headers.get
        self.headers = type("H", (), {"get": lambda s, k, d="": ({"Authorization": auth} if auth else {}).get(k, d)})()


def _make_user(test_db, role="admin"):
    user, _ = create_user(test_db, f"{role}@example.com")
    user.role = role
    test_db.commit()
    return user


def test_get_current_user_jwt_success(test_db):
    user = _make_user(test_db, "user")
    token = get_token_manager().create_access_token(user.id, user.email, UserRole.USER)
    req = _FakeRequest(f"Bearer {token}")
    result = asyncio.run(get_current_user_jwt(req, test_db))
    assert result.id == user.id


def test_get_current_user_jwt_missing_header(test_db):
    with pytest.raises(HTTPException) as ei:
        asyncio.run(get_current_user_jwt(_FakeRequest(""), test_db))
    assert ei.value.status_code == 401


def test_get_current_user_jwt_invalidated_session(test_db):
    user = _make_user(test_db, "user")
    token = get_token_manager().create_access_token(user.id, user.email, UserRole.USER)
    get_session_manager().invalidate_session(token, user.id)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(get_current_user_jwt(_FakeRequest(f"Bearer {token}"), test_db))
    assert "invalidated" in ei.value.detail.lower()


def test_get_current_user_jwt_unknown_user(test_db):
    token = get_token_manager().create_access_token("ghost_id", "g@x.com", UserRole.USER)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(get_current_user_jwt(_FakeRequest(f"Bearer {token}"), test_db))
    assert ei.value.status_code == 401


def test_require_permission_allows_and_denies(test_db):
    admin = _make_user(test_db, "admin")
    free = _make_user(test_db, "free")
    check = require_permission("users:write_all")
    assert asyncio.run(check(admin)) is admin
    with pytest.raises(HTTPException) as ei:
        asyncio.run(check(free))
    assert ei.value.status_code == 403


def test_require_role_hierarchy(test_db):
    admin = _make_user(test_db, "admin")
    moderator = _make_user(test_db, "moderator")
    user = _make_user(test_db, "user")
    need_mod = require_role(UserRole.MODERATOR)
    assert asyncio.run(need_mod(admin)) is admin       # admin always allowed
    assert asyncio.run(need_mod(moderator)) is moderator
    with pytest.raises(HTTPException) as ei:
        asyncio.run(need_mod(user))                     # user < moderator
    assert ei.value.status_code == 403
