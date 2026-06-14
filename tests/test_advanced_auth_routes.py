"""
Integration tests for api/routers/advanced_auth.py — OAuth2, JWT, RBAC, session endpoints.

Uses TestClient + test_db fixture (from conftest.py) so no real database is touched.
OAuth network calls are intercepted via httpx.MockTransport or monkeypatching.
"""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import app, get_db
from api.db import create_user, hash_password
from api.advanced_auth import (
    get_token_manager,
    get_session_manager,
    UserRole,
    generate_oauth_state,
)


# ── shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def client(test_db):
    """TestClient wired to the test database."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def jwt_user(test_db):
    """User with a password hash (for JWT-based auth tests)."""
    user, _ = create_user(test_db, email="jwt@test.com")
    user.password_hash = hash_password("TestPass123!")
    user.role = "user"
    test_db.commit()
    return user


@pytest.fixture
def admin_jwt_user(test_db):
    """Admin user for RBAC tests."""
    user, _ = create_user(test_db, email="admin@test.com")
    user.role = "admin"
    user.password_hash = hash_password("AdminPass123!")
    test_db.commit()
    return user


def _make_bearer(user, role=UserRole.USER):
    """Mint a valid JWT access token for the given user."""
    return get_token_manager().create_access_token(user.id, user.email, role)


# ── GET /auth/roles  (no auth required) ───────────────────────────────────────

class TestListRoles:
    def test_list_roles_returns_all(self, client):
        resp = client.get("/auth/roles")
        assert resp.status_code == 200
        data = resp.json()
        assert "roles" in data
        names = {r["name"] for r in data["roles"]}
        assert {"admin", "moderator", "user", "free"} == names


# ── GET /auth/oauth/github (start flow) ───────────────────────────────────────

class TestGitHubOAuthStart:
    def test_github_oauth_not_configured(self, client, monkeypatch):
        """If GITHUB_OAUTH_CLIENT_ID is unset → 501."""
        monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "")
        # Re-create oauth singleton with patched env
        import api.advanced_auth as aa
        old = aa._github_oauth
        aa._github_oauth = aa.GitHubOAuth2()
        monkeypatch.setattr(aa, "_github_oauth", aa._github_oauth)

        resp = client.get("/auth/oauth/github")
        assert resp.status_code == 501
        assert "not configured" in resp.json()["detail"].lower()

        aa._github_oauth = old

    def test_github_oauth_configured(self, client, monkeypatch):
        """When client_id set, returns auth_url and state."""
        import api.advanced_auth as aa
        old = aa._github_oauth
        monkeypatch.setattr(aa, "_github_oauth", aa.GitHubOAuth2.__new__(aa.GitHubOAuth2))
        aa._github_oauth.client_id = "gh_client_id"
        aa._github_oauth.client_secret = "gh_secret"
        aa._github_oauth.redirect_uri = "http://localhost/cb"

        resp = client.get("/auth/oauth/github")
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert "state" in data
        assert "github.com" in data["auth_url"]

        aa._github_oauth = old


# ── GET /auth/oauth/google (start flow) ───────────────────────────────────────

class TestGoogleOAuthStart:
    def test_google_oauth_not_configured(self, client, monkeypatch):
        """If GOOGLE_OAUTH_CLIENT_ID is unset → 501."""
        import api.advanced_auth as aa
        old = aa._google_oauth
        monkeypatch.setattr(aa, "_google_oauth", aa.GoogleOAuth2.__new__(aa.GoogleOAuth2))
        aa._google_oauth.client_id = ""
        aa._google_oauth.client_secret = ""
        aa._google_oauth.redirect_uri = ""

        resp = client.get("/auth/oauth/google")
        assert resp.status_code == 501

        aa._google_oauth = old

    def test_google_oauth_configured(self, client, monkeypatch):
        """When client_id set, returns auth_url and state."""
        import api.advanced_auth as aa
        old = aa._google_oauth
        monkeypatch.setattr(aa, "_google_oauth", aa.GoogleOAuth2.__new__(aa.GoogleOAuth2))
        aa._google_oauth.client_id = "g_client_id"
        aa._google_oauth.client_secret = "g_secret"
        aa._google_oauth.redirect_uri = "http://localhost/gcb"

        resp = client.get("/auth/oauth/google")
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert "google.com" in data["auth_url"]

        aa._google_oauth = old


# ── GET /auth/oauth/github/callback ──────────────────────────────────────────

class TestGitHubCallback:
    """Test the GitHub OAuth2 callback with mocked network calls."""

    def _mock_transport(self):
        """Return httpx MockTransport that fakes GitHub token + user API."""
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "access_token" in url or "login/oauth" in url:
                return httpx.Response(200, json={"access_token": "gh_access_token"})
            # /user endpoint
            return httpx.Response(
                200,
                json={"id": 42, "login": "testuser", "email": "ghuser@test.com"},
            )
        return httpx.MockTransport(handler)

    def test_callback_invalid_state(self, client):
        """Bad state string → 400."""
        resp = client.get("/auth/oauth/github/callback?code=abc&state=bad_state")
        assert resp.status_code == 400

    def test_callback_success_creates_user_and_returns_tokens(self, client, monkeypatch):
        """Valid callback creates user, returns access + refresh tokens."""
        transport = self._mock_transport()
        real_client = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))

        state = generate_oauth_state("temp", "github")
        resp = client.get(f"/auth/oauth/github/callback?code=auth_code&state={state}")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["email"] == "ghuser@test.com"

    def test_callback_no_access_token_in_response(self, client, monkeypatch):
        """If GitHub returns no access_token → 400."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"error": "bad_verification_code"})

        transport = httpx.MockTransport(handler)
        real_client = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))

        state = generate_oauth_state("temp", "github")
        resp = client.get(f"/auth/oauth/github/callback?code=bad_code&state={state}")
        assert resp.status_code == 400
        assert "Failed to get access token" in resp.json()["detail"]

    def test_callback_no_email_in_user_info(self, client, monkeypatch):
        """If GitHub user has no email → 400."""
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "login/oauth" in url:
                return httpx.Response(200, json={"access_token": "gh_tok"})
            # User info without email
            return httpx.Response(200, json={"id": 99, "login": "nomail"})

        transport = httpx.MockTransport(handler)
        real_client = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))

        state = generate_oauth_state("temp", "github")
        resp = client.get(f"/auth/oauth/github/callback?code=c&state={state}")
        assert resp.status_code == 400
        assert "user info" in resp.json()["detail"].lower()

    def test_callback_existing_user_updates_credential(self, client, monkeypatch, test_db):
        """Callback for existing user updates their OAuth credential."""
        # Create a user with the same email first
        create_user(test_db, email="ghuser@test.com")

        transport = self._mock_transport()
        real_client = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))

        state = generate_oauth_state("temp", "github")
        resp = client.get(f"/auth/oauth/github/callback?code=code&state={state}")
        assert resp.status_code == 200
        assert resp.json()["email"] == "ghuser@test.com"


# ── GET /auth/oauth/google/callback ──────────────────────────────────────────

class TestGoogleCallback:
    def _mock_transport(self):
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "token" in url:
                return httpx.Response(200, json={"access_token": "g_access_token"})
            # userinfo endpoint
            return httpx.Response(
                200,
                json={"sub": "google_sub_123", "email": "guser@test.com"},
            )
        return httpx.MockTransport(handler)

    def test_callback_invalid_state(self, client):
        resp = client.get("/auth/oauth/google/callback?code=abc&state=garbage")
        assert resp.status_code == 400

    def test_callback_success(self, client, monkeypatch):
        transport = self._mock_transport()
        real_client = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))

        state = generate_oauth_state("temp", "google")
        resp = client.get(f"/auth/oauth/google/callback?code=auth_code&state={state}")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == "guser@test.com"

    def test_callback_no_access_token(self, client, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        transport = httpx.MockTransport(handler)
        real_client = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))

        state = generate_oauth_state("temp", "google")
        resp = client.get(f"/auth/oauth/google/callback?code=bad&state={state}")
        assert resp.status_code == 400

    def test_callback_no_email_or_sub(self, client, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "token" in url:
                return httpx.Response(200, json={"access_token": "g_tok"})
            return httpx.Response(200, json={})

        transport = httpx.MockTransport(handler)
        real_client = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))

        state = generate_oauth_state("temp", "google")
        resp = client.get(f"/auth/oauth/google/callback?code=c&state={state}")
        assert resp.status_code == 400


# ── POST /auth/oauth/token (refresh) ─────────────────────────────────────────

class TestRefreshToken:
    def test_refresh_returns_new_access_token(self, client, jwt_user):
        refresh = get_token_manager().create_refresh_token(jwt_user.id, jwt_user.email)
        resp = client.post(f"/auth/oauth/token?refresh_token={refresh}")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 900

    def test_refresh_with_access_token_fails(self, client, jwt_user):
        """Passing an access token (not refresh) → 401."""
        access = _make_bearer(jwt_user)
        resp = client.post(f"/auth/oauth/token?refresh_token={access}")
        assert resp.status_code == 401
        assert "Invalid token type" in resp.json()["detail"]

    def test_refresh_with_invalid_token_fails(self, client):
        resp = client.post("/auth/oauth/token?refresh_token=not.valid.jwt")
        assert resp.status_code == 401

    def test_refresh_for_deleted_user_fails(self, client, test_db):
        """Refresh token for soft-deleted user → 401."""
        from datetime import datetime, timezone
        user, _ = create_user(test_db, email="deleted@test.com")
        user.deleted_at = datetime.now(timezone.utc)
        test_db.commit()

        refresh = get_token_manager().create_refresh_token(user.id, user.email)
        resp = client.post(f"/auth/oauth/token?refresh_token={refresh}")
        assert resp.status_code == 401


# ── POST /auth/logout ─────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_success(self, client, jwt_user):
        token = _make_bearer(jwt_user)
        resp = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "logged_out"
        assert data["user_id"] == jwt_user.id

    def test_logout_missing_auth_header(self, client):
        resp = client.post("/auth/logout")
        assert resp.status_code == 401

    def test_logout_invalid_token(self, client):
        resp = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer invalid.jwt.here"},
        )
        assert resp.status_code == 401


# ── POST /auth/logout/all ─────────────────────────────────────────────────────

class TestLogoutAll:
    def test_logout_all_success(self, client, jwt_user):
        token = _make_bearer(jwt_user)
        resp = client.post(
            "/auth/logout/all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "all_sessions_invalidated"
        assert data["user_id"] == jwt_user.id

    def test_logout_all_requires_auth(self, client):
        resp = client.post("/auth/logout/all")
        assert resp.status_code == 401


# ── GET /auth/me ──────────────────────────────────────────────────────────────

class TestGetMe:
    def test_get_me_success(self, client, jwt_user):
        token = _make_bearer(jwt_user)
        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == jwt_user.id
        assert data["email"] == jwt_user.email
        assert "role" in data
        assert "oauth_providers" in data

    def test_get_me_requires_auth(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401


# ── PATCH /auth/me/password ───────────────────────────────────────────────────

class TestChangePassword:
    def test_change_password_success(self, client, jwt_user):
        token = _make_bearer(jwt_user)
        resp = client.patch(
            "/auth/me/password",
            params={
                "old_password": "TestPass123!",
                "new_password": "NewPass456@",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "password_changed"

    def test_change_password_wrong_old_password(self, client, jwt_user):
        token = _make_bearer(jwt_user)
        resp = client.patch(
            "/auth/me/password",
            params={
                "old_password": "WrongPassword1!",
                "new_password": "NewPass456@",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert "Invalid password" in resp.json()["detail"]

    def test_change_password_weak_new_password(self, client, jwt_user):
        token = _make_bearer(jwt_user)
        resp = client.patch(
            "/auth/me/password",
            params={
                "old_password": "TestPass123!",
                "new_password": "weak",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_change_password_no_existing_password(self, client, test_db):
        """User without password_hash → 401."""
        user, _ = create_user(test_db, email="nopass@test.com")
        # No password_hash set
        token = get_token_manager().create_access_token(user.id, user.email, UserRole.USER)
        resp = client.patch(
            "/auth/me/password",
            params={
                "old_password": "AnyPassword123!",
                "new_password": "NewPass456@",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    def test_change_password_requires_auth(self, client):
        resp = client.patch(
            "/auth/me/password",
            params={"old_password": "x", "new_password": "y"},
        )
        assert resp.status_code == 401


# ── GET /auth/permissions ─────────────────────────────────────────────────────

class TestPermissions:
    def test_get_permissions_admin(self, client, admin_jwt_user):
        token = get_token_manager().create_access_token(
            admin_jwt_user.id, admin_jwt_user.email, UserRole.ADMIN
        )
        resp = client.get(
            "/auth/permissions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "admin"
        assert "users:write_all" in data["permissions"]

    def test_get_permissions_user(self, client, jwt_user):
        token = _make_bearer(jwt_user)
        resp = client.get(
            "/auth/permissions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "personas:read" in data["permissions"]

    def test_get_permissions_requires_auth(self, client):
        resp = client.get("/auth/permissions")
        assert resp.status_code == 401


# ── GET /auth/users/{user_id} ─────────────────────────────────────────────────

class TestGetUserProfile:
    def test_get_user_as_admin(self, client, admin_jwt_user, jwt_user):
        token = get_token_manager().create_access_token(
            admin_jwt_user.id, admin_jwt_user.email, UserRole.ADMIN
        )
        resp = client.get(
            f"/auth/users/{jwt_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == jwt_user.id

    def test_get_user_not_found(self, client, admin_jwt_user):
        token = get_token_manager().create_access_token(
            admin_jwt_user.id, admin_jwt_user.email, UserRole.ADMIN
        )
        resp = client.get(
            "/auth/users/nonexistent-id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_get_user_requires_admin(self, client, jwt_user):
        token = _make_bearer(jwt_user, UserRole.USER)
        resp = client.get(
            f"/auth/users/{jwt_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ── PATCH /auth/users/{user_id}/role ─────────────────────────────────────────

class TestUpdateUserRole:
    def test_update_role_success(self, client, admin_jwt_user, jwt_user):
        token = get_token_manager().create_access_token(
            admin_jwt_user.id, admin_jwt_user.email, UserRole.ADMIN
        )
        resp = client.patch(
            f"/auth/users/{jwt_user.id}/role?new_role=moderator",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "moderator"

    def test_update_role_invalid_role(self, client, admin_jwt_user, jwt_user):
        token = get_token_manager().create_access_token(
            admin_jwt_user.id, admin_jwt_user.email, UserRole.ADMIN
        )
        resp = client.patch(
            f"/auth/users/{jwt_user.id}/role?new_role=superuser",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "Invalid role" in resp.json()["detail"]

    def test_update_role_user_not_found(self, client, admin_jwt_user):
        token = get_token_manager().create_access_token(
            admin_jwt_user.id, admin_jwt_user.email, UserRole.ADMIN
        )
        resp = client.patch(
            "/auth/users/no-such-user/role?new_role=user",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_update_role_requires_admin(self, client, jwt_user):
        token = _make_bearer(jwt_user, UserRole.USER)
        resp = client.patch(
            f"/auth/users/{jwt_user.id}/role?new_role=admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ── DELETE /auth/users/{user_id} ──────────────────────────────────────────────

class TestDeleteUser:
    def test_delete_user_success(self, client, admin_jwt_user, jwt_user):
        token = get_token_manager().create_access_token(
            admin_jwt_user.id, admin_jwt_user.email, UserRole.ADMIN
        )
        resp = client.delete(
            f"/auth/users/{jwt_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "user_deleted"
        assert "deleted_at" in data

    def test_delete_user_not_found(self, client, admin_jwt_user):
        token = get_token_manager().create_access_token(
            admin_jwt_user.id, admin_jwt_user.email, UserRole.ADMIN
        )
        resp = client.delete(
            "/auth/users/ghost-id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_delete_user_requires_admin(self, client, jwt_user):
        token = _make_bearer(jwt_user, UserRole.USER)
        resp = client.delete(
            f"/auth/users/{jwt_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
