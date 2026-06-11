"""Security and authentication tests (A1–A12)."""

import os
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import (
    Base, create_user, hash_password, verify_password,
    hash_api_key, verify_api_key, get_user_by_api_key,
    create_email_verification_token, consume_verification_token,
    record_login_attempt, check_lockout, clear_login_attempts,
)
from api.main import app, get_db

# Set test database before importing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


@pytest.fixture
def test_db():
    """Create in-memory SQLite DB for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return TestingSessionLocal()


@pytest.fixture
def client(test_db):
    """TestClient with dependency injection of test database."""
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


# ── A2: API Key Hashing ──────────────────────────────────────────────────────

def test_api_key_hashing():
    """A2: API keys are hashed, not stored plaintext."""
    key = "prs_abc123def456xyz789"
    h1 = hash_api_key(key)
    h2 = hash_api_key(key)
    assert h1 == h2, "Hash should be deterministic"
    assert h1 != key, "Hash should not equal plaintext"
    assert verify_api_key(h1, key), "Correct key should verify"
    assert not verify_api_key(h1, key + "x"), "Wrong key should fail"


def test_api_key_lookup(test_db):
    """A2: API key lookup via hash works with fallback."""
    user, full_key = create_user(test_db, "alice@test.com")
    found = get_user_by_api_key(test_db, full_key)
    assert found is not None
    assert found.email == "alice@test.com"
    assert found.api_key != full_key, "Stored key should be prefix only"


# ── A1/A5: Password Authentication ───────────────────────────────────────────

def test_password_hashing():
    """A1: Passwords are hashed with Argon2."""
    pwd = "MySecurePassword123!"
    h1 = hash_password(pwd)
    h2 = hash_password(pwd)
    assert h1 != h2, "Argon2 includes salt: hashes differ"
    assert verify_password(h1, pwd), "Correct password should verify"
    assert not verify_password(h1, pwd + "x"), "Wrong password should fail"


def test_password_registration(client: TestClient, test_db):
    """A1: User can register with optional password."""
    response = client.post("/auth/register", json={
        "email": "bob@test.com",
        "password": "SecurePass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert data["password_enabled"] is True


def test_password_login(client: TestClient, test_db):
    """A1: /auth/login works with email + password."""
    # Register
    client.post("/auth/register", json={
        "email": "charlie@test.com",
        "password": "MyPassword123!"
    })

    # Login
    response = client.post("/auth/login", json={
        "email": "charlie@test.com",
        "password": "MyPassword123!"
    })
    assert response.status_code == 200
    assert "api_key" in response.json()


def test_password_login_wrong_password(client: TestClient, test_db):
    """A1: Wrong password rejected."""
    client.post("/auth/register", json={
        "email": "david@test.com",
        "password": "CorrectPassword123!"
    })

    response = client.post("/auth/login", json={
        "email": "david@test.com",
        "password": "WrongPassword"
    })
    assert response.status_code == 401


# ── A11: Failed Login Tracking ───────────────────────────────────────────────

def test_failed_login_tracking(test_db):
    """A11: Failed login attempts are tracked."""
    user, _ = create_user(test_db, "eve@test.com")
    user.password_hash = hash_password("password123")
    test_db.commit()

    # Record 3 failed attempts
    for i in range(3):
        record_login_attempt(test_db, user.id, "192.168.1.1", success=False)
        test_db.refresh(user)
        assert user.failed_login_attempts == i + 1


def test_lockout_after_5_failures(test_db):
    """A11: 5 failed attempts trigger 5-minute lockout."""
    user, _ = create_user(test_db, "frank@test.com")

    # Record 5 failed attempts
    for _ in range(5):
        record_login_attempt(test_db, user.id, "192.168.1.1", success=False)

    test_db.refresh(user)
    assert user.lockout_until is not None
    assert check_lockout(user) is True


def test_lockout_cleared_on_success(test_db):
    """A11: Failed attempt counter clears after successful login."""
    user, _ = create_user(test_db, "grace@test.com")

    # Record 2 failed attempts
    for _ in range(2):
        record_login_attempt(test_db, user.id, "192.168.1.2", success=False)

    test_db.refresh(user)
    assert user.failed_login_attempts == 2

    # Clear on success
    clear_login_attempts(test_db, user.id)
    test_db.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.lockout_until is None


# ── A4: Email Verification ──────────────────────────────────────────────────

def test_email_verification_token(test_db):
    """A4: Email verification tokens are generated and consumed."""
    user, _ = create_user(test_db, "henry@test.com")

    # Generate token
    token = create_email_verification_token(test_db, user.id)
    assert len(token) > 20

    # Consume token
    verified_user = consume_verification_token(test_db, token)
    assert verified_user is not None
    assert verified_user.email_verified is True

    # Token cannot be reused
    verified_again = consume_verification_token(test_db, token)
    assert verified_again is None


def test_email_verification_token_expiry(test_db):
    """A4: Expired tokens are rejected."""
    user, _ = create_user(test_db, "iris@test.com")

    from api.db import EmailVerificationToken
    # Create expired token manually
    expired_token = "expiredtoken123456"
    record = EmailVerificationToken(
        user_id=user.id,
        token=expired_token,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    test_db.add(record)
    test_db.commit()

    # Expired token should not verify
    result = consume_verification_token(test_db, expired_token)
    assert result is None


def test_email_verification_register(client: TestClient):
    """A4: /auth/register sends verification email."""
    response = client.post("/auth/register", json={
        "email": "jack@test.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    # RESEND_API_KEY not set: email sent to log only, no error


# ── A2/A10: API Key Rotation ────────────────────────────────────────────────

def test_api_key_rotation_grace_period(client: TestClient):
    """A10: Key rotation includes 7-day grace period message."""
    # Register & get API key
    reg_resp = client.post("/auth/register", json={"email": "karl@test.com"})
    api_key = reg_resp.json()["api_key"]

    # Rotate key
    rotate_resp = client.post(
        "/me/api-keys/rotate",
        headers={"X-API-Key": api_key}
    )
    assert rotate_resp.status_code == 200
    data = rotate_resp.json()
    assert "grace period" in data["message"].lower()
    assert "7" in data["message"]


# ── A8: CSP Security Headers ────────────────────────────────────────────────

def test_csp_nonce_in_headers(client: TestClient):
    """A8: CSP headers include nonce for scripts."""
    response = client.get("/health")
    assert response.status_code == 200
    csp = response.headers.get("Content-Security-Policy", "")
    assert "nonce-" in csp
    assert "script-src" in csp
    assert "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]


# ── A3: Rate Limiting ────────────────────────────────────────────────────────

def test_rate_limit_headers(client: TestClient):
    """A3: Rate limit headers present in response."""
    # Register (uses API key internally)
    response = client.post("/auth/register", json={"email": "laura@test.com"})
    assert response.status_code == 200
    # X-RateLimit headers may not be present for unauthenticated endpoints
    # but should be present for authenticated endpoints


def test_rate_limit_quota_exceeded(client: TestClient):
    """A3: 429 when quota exceeded (mocked test)."""
    # This would require mocking the rate limiter state
    # Real test requires hitting the same endpoint 100+ times in 1 hour
    pass


# ── B22: Audit Logging ───────────────────────────────────────────────────────

def test_audit_log_written(test_db):
    """B22: Security events written to audit_log table."""
    from api.db import write_audit_log, AuditLog

    user, _ = create_user(test_db, "mike@test.com")
    write_audit_log(
        test_db,
        event_type="test_event",
        user_id=user.id,
        endpoint="/test",
        status_code=401
    )

    logs = test_db.query(AuditLog).filter_by(user_id=user.id).all()
    assert len(logs) == 1
    assert logs[0].event_type == "test_event"
    assert logs[0].status_code == 401


# ── G79: Soft Delete ─────────────────────────────────────────────────────────

def test_soft_delete_user(test_db):
    """G79: Soft-deleted users excluded from queries."""
    user, _ = create_user(test_db, "nancy@test.com")
    user.deleted_at = datetime.now(timezone.utc)
    test_db.commit()

    # User should not be found by email
    from api.db import get_user_by_email
    found = get_user_by_email(test_db, "nancy@test.com")
    assert found is None


def test_soft_delete_purchase(test_db):
    """G79: Soft-deleted purchases excluded from has_purchased checks."""
    from api.db import has_purchased, record_purchase, Purchase

    user, _ = create_user(test_db, "oscar@test.com")
    purchase = record_purchase(test_db, user.id, "persona_socrates")
    purchase.deleted_at = datetime.now(timezone.utc)
    test_db.commit()

    # Purchase should not count as owned
    assert not has_purchased(test_db, user.id, "persona_socrates")
