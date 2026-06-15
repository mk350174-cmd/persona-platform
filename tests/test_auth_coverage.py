"""
Tests to improve coverage for api/auth.py.

Targets missed lines:
  43-45  → Bearer token parsing in _require_api_key
  67     → get_current_user: API key not found
  92     → require_persona_access: free persona early return
  119-120 → authenticate_password: locked-out user path
  130    → authenticate_password: active=False after correct password
  138-139 → authenticate_password: user not found, dummy hash path
"""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_mock")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from api.db import Base, create_user, hash_password, User, verify_password
from api.main import app, get_db
from api.catalog import PERSONA_CATALOG


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "auth_cov.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db):
    user, full_key = create_user(test_db, "authcov@example.com")
    user.password_hash = hash_password("secret123")
    test_db.commit()
    return user, full_key


# ── _require_api_key: Bearer token path (lines 43-45) ─────────────────────────

class TestBearerTokenParsing:
    """Test the Authorization: Bearer prs_... header path."""

    def test_bearer_token_valid_grants_access(self, client, test_user):
        """Bearer Authorization header with valid prs_ key should succeed."""
        user, full_key = test_user
        response = client.get(
            "/me",
            headers={"Authorization": f"Bearer {full_key}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == user.email

    def test_bearer_token_without_prs_prefix_rejected(self, client):
        """Bearer token without prs_ prefix should be treated as missing key."""
        response = client.get(
            "/me",
            headers={"Authorization": "Bearer invalid_token_no_prs"},
        )
        assert response.status_code == 401

    def test_bearer_token_malformed_single_part(self, client):
        """Authorization header with only one word (no space) should be rejected."""
        response = client.get(
            "/me",
            headers={"Authorization": "onlyonepart"},
        )
        assert response.status_code == 401

    def test_bearer_token_wrong_scheme(self, client):
        """Authorization header with wrong scheme (not Bearer) should be rejected."""
        response = client.get(
            "/me",
            headers={"Authorization": "Token prs_somethingvalid_but_wrong_scheme"},
        )
        assert response.status_code == 401

    def test_x_api_key_header_still_works(self, client, test_user):
        """X-API-Key header should still grant access as fallback."""
        user, full_key = test_user
        response = client.get(
            "/me",
            headers={"X-API-Key": full_key},
        )
        assert response.status_code == 200


# ── _require_api_key: missing key (line 51-55 already covered) ────────────────

class TestMissingApiKey:
    """Test 401 when no key is provided."""

    def test_no_key_returns_401(self, client):
        response = client.get("/me")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_x_api_key_without_prs_prefix_rejected(self, client):
        """X-API-Key header without prs_ prefix should not be accepted."""
        response = client.get(
            "/me",
            headers={"X-API-Key": "notprs_shouldfail"},
        )
        assert response.status_code == 401


# ── get_current_user: key not found (line 67) ─────────────────────────────────

class TestGetCurrentUserKeyNotFound:
    """Test that a syntactically valid but non-existent key returns 401."""

    def test_valid_format_but_nonexistent_key(self, client):
        """prs_ key that doesn't exist in DB should return 401."""
        fake_key = "prs_" + "a" * 56  # valid format, not in DB
        response = client.get(
            "/me",
            headers={"X-API-Key": fake_key},
        )
        assert response.status_code == 401
        assert "not found" in response.json()["detail"].lower() or \
               "inactive" in response.json()["detail"].lower() or \
               "invalid" in response.json()["detail"].lower()


# ── require_persona_access: free persona skip (line 92) ───────────────────────

class TestRequirePersonaAccessFree:
    """Test that free personas (price_usd == 0) bypass purchase check."""

    def test_free_persona_access_no_purchase_needed(self, test_db, test_user):
        """require_persona_access should return without error for price_usd == 0."""
        from api.auth import require_persona_access
        from unittest.mock import patch
        import api.catalog as catalog_mod

        user, _ = test_user

        # PERSONA_CATALOG is imported inside require_persona_access from api.catalog;
        # patch it at its source module.
        free_persona_meta = {"price_usd": 0, "name": "Free Test Persona"}
        with patch.dict(catalog_mod.PERSONA_CATALOG, {"free_persona": free_persona_meta}):
            # Should not raise
            require_persona_access("free_persona", user, test_db)

    def test_paid_persona_without_purchase_raises_403(self, test_db, test_user):
        """require_persona_access should raise 403 if persona is paid and not purchased."""
        from api.auth import require_persona_access
        from fastapi import HTTPException
        from unittest.mock import patch
        import api.catalog as catalog_mod

        user, _ = test_user

        paid_persona_meta = {"price_usd": 29, "name": "Paid Test Persona"}
        with patch.dict(catalog_mod.PERSONA_CATALOG, {"paid_persona": paid_persona_meta}):
            with pytest.raises(HTTPException) as exc_info:
                require_persona_access("paid_persona", user, test_db)
            assert exc_info.value.status_code == 403

    def test_nonexistent_persona_raises_404(self, test_db, test_user):
        """require_persona_access should raise 404 for unknown persona_id."""
        from api.auth import require_persona_access
        from fastapi import HTTPException

        user, _ = test_user
        with pytest.raises(HTTPException) as exc_info:
            require_persona_access("does_not_exist_xyz", user, test_db)
        assert exc_info.value.status_code == 404


# ── authenticate_password: lockout path (lines 119-120) ──────────────────────

class TestAuthenticatePasswordLockout:
    """Test the lockout branch in authenticate_password."""

    def test_locked_out_user_gets_429(self, client, test_user, test_db):
        """Locked-out user should receive 429 Too Many Requests on login."""
        user, _ = test_user

        # Simulate lockout by patching check_lockout to return True
        with patch("api.auth.check_lockout", return_value=True), \
             patch("api.auth.record_login_attempt") as mock_record:
            response = client.post(
                "/auth/login",
                json={"email": user.email, "password": "secret123"},
            )
            assert response.status_code == 429
            assert "locked" in response.json()["detail"].lower()
            # record_login_attempt should have been called with success=False
            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args
            assert call_kwargs.kwargs.get("success") is False or \
                   call_kwargs.args[-1] is False


# ── authenticate_password: inactive user after correct password (line 130) ────

class TestAuthenticatePasswordInactiveUser:
    """Test branch where password is correct but user is inactive."""

    def test_inactive_user_returns_401_after_correct_password(self, client, test_db):
        """An inactive user with correct password should still get 401."""
        user, full_key = create_user(test_db, "inactive@example.com")
        user.password_hash = hash_password("correct_pass")
        user.active = False
        test_db.commit()

        response = client.post(
            "/auth/login",
            json={"email": "inactive@example.com", "password": "correct_pass"},
        )
        assert response.status_code == 401
        detail = response.json()["detail"].lower()
        assert "inactive" in detail or "deleted" in detail or "invalid" in detail


# ── authenticate_password: user not found dummy hash (lines 138-139) ──────────

class TestAuthenticatePasswordUserNotFound:
    """Test timing-safe branch when user is not in the database."""

    def test_nonexistent_email_still_hashes_and_returns_401(self, client):
        """Non-existent email should trigger dummy hash (anti-timing) and return 401."""
        response = client.post(
            "/auth/login",
            json={"email": "nobody@nowhere.com", "password": "anypassword"},
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_nonexistent_email_calls_hash_password(self, client):
        """Verify hash_password is called for non-existent user (timing attack prevention).

        hash_password is imported inside the function body from api.db, so we patch it there.
        """
        with patch("api.db.hash_password") as mock_hash:
            mock_hash.return_value = "dummy_hash"
            response = client.post(
                "/auth/login",
                json={"email": "ghost@example.com", "password": "password"},
            )
            assert response.status_code == 401
            mock_hash.assert_called_once_with("password")
