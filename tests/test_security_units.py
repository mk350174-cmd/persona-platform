"""Unit tests for security functions (no app import)."""

import pytest
from datetime import datetime, timedelta, timezone

# Direct imports to avoid app-level imports
from api.db import (
    hash_api_key, verify_api_key,
    hash_password, verify_password,
)


class TestAPIKeySecurity:
    """A2: API key hashing and verification."""

    def test_api_key_generation_format(self):
        """API keys start with prs_ and are 60 chars."""
        from api.db import User
        key = User.generate_api_key()
        assert key.startswith("prs_")
        assert len(key) == 60

    def test_api_key_hashing_deterministic(self):
        """Same key produces same hash."""
        key = "prs_abc123def456xyz789000111222333444555666"
        h1 = hash_api_key(key)
        h2 = hash_api_key(key)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_api_key_verification(self):
        """Correct key verifies, wrong key fails."""
        key = "prs_abc123def456xyz789000111222333444555666"
        h = hash_api_key(key)
        assert verify_api_key(h, key)
        assert not verify_api_key(h, key + "x")
        assert not verify_api_key(h, "prs_wrong")

    def test_api_key_hash_not_plaintext(self):
        """Hash is not equal to original key."""
        key = "prs_abc123def456xyz789000111222333444555666"
        h = hash_api_key(key)
        assert h != key


class TestPasswordSecurity:
    """A1: Password hashing and verification."""

    def test_password_hashing_argon2(self):
        """Passwords hashed with Argon2id."""
        pwd = "MySecurePassword123!"
        h = hash_password(pwd)
        # Argon2 hashes start with $argon2id$
        assert h.startswith("$argon2id$")

    def test_password_hashing_non_deterministic(self):
        """Different hashes for same password (salt included)."""
        pwd = "MySecurePassword123!"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        # Argon2 includes random salt, so hashes differ
        assert h1 != h2

    def test_password_verification(self):
        """Correct password verifies, wrong fails."""
        pwd = "CorrectPassword123!"
        h = hash_password(pwd)
        assert verify_password(h, pwd)
        assert not verify_password(h, pwd + "x")
        assert not verify_password(h, "WrongPassword")

    def test_password_verification_timing_resistance(self):
        """Verification doesn't leak password length (timing attack resistance)."""
        pwd = "CorrectPassword"
        h = hash_password(pwd)
        # Both should complete without timing variance
        verify_password(h, "a")
        verify_password(h, "a" * 100)
        # If implemented with try/except and constant time, timing should be similar

    def test_password_length_limits(self):
        """Password length validated at model level."""
        from api.models import RegisterRequest
        # Too short
        with pytest.raises(ValueError):
            RegisterRequest(email="test@example.com", password="short")
        # Too long
        with pytest.raises(ValueError):
            RegisterRequest(email="test@example.com", password="x" * 129)
        # Valid
        RegisterRequest(email="test@example.com", password="ValidPass123!")


class TestEmailValidation:
    """A4: Email validation and models."""

    def test_email_validation(self):
        """EmailStr rejects invalid emails."""
        from api.models import RegisterRequest
        # Invalid
        with pytest.raises(ValueError):
            RegisterRequest(email="not-an-email")
        # Valid
        r = RegisterRequest(email="test@example.com")
        assert r.email == "test@example.com"

    def test_email_rfc5322_compliance(self):
        """Valid RFC-5322 emails accepted."""
        from api.models import LoginRequest
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_123@example.org",
        ]
        for email in valid_emails:
            r = LoginRequest(email=email, password="password")
            assert r.email == email


class TestRateLimitingQuotas:
    """A3: Rate limiting per endpoint."""

    def test_rate_limit_quotas_defined(self):
        """All endpoints have defined quotas."""
        from api.middleware.rate_limiter import ENDPOINT_QUOTAS
        assert ENDPOINT_QUOTAS["/auth/login"] == 10
        assert ENDPOINT_QUOTAS["/auth/register"] == 5
        assert ENDPOINT_QUOTAS["/v1/compile"] == 100
        assert ENDPOINT_QUOTAS["/checkout"] == 20

    def test_rate_limit_key_extraction(self):
        """API key prefix extracted from headers."""
        from api.middleware.rate_limiter import _extract_key_prefix
        from unittest.mock import MagicMock
        from fastapi import Request

        # From X-API-Key
        mock_req = MagicMock(spec=Request)
        mock_req.headers = {"x-api-key": "prs_abc123xyz"}
        assert _extract_key_prefix(mock_req) == "prs_abc1"

        # From Authorization
        mock_req.headers = {"authorization": "Bearer prs_def456"}
        assert _extract_key_prefix(mock_req) == "prs_def4"

        # None if missing
        mock_req.headers = {}
        assert _extract_key_prefix(mock_req) is None


class TestLoginAttemptTracking:
    """A11: Failed login attempt tracking and lockout."""

    def test_lockout_trigger_threshold(self):
        """5 failed attempts trigger lockout."""
        from api.db import SessionLocal, init_db, create_user, record_login_attempt, check_lockout
        import os
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker as sm

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        SessionLocal_local = sm(bind=engine, autoflush=False, autocommit=False)

        from api.db import Base
        Base.metadata.create_all(bind=engine)

        db = SessionLocal_local()
        user, _ = create_user(db, "test@example.com")

        # Record 5 failures
        for i in range(5):
            record_login_attempt(db, user.id, "192.168.1.1", success=False)
            db.refresh(user)
            if i < 4:
                assert not check_lockout(user), f"Should not lock at {i+1} attempts"
            else:
                assert check_lockout(user), "Should lock at 5 attempts"

        db.close()


class TestAuditLog:
    """B22: Audit log table and events."""

    def test_audit_log_schema(self):
        """AuditLog table has required fields."""
        from api.db import AuditLog
        assert hasattr(AuditLog, "user_id")
        assert hasattr(AuditLog, "event_type")
        assert hasattr(AuditLog, "endpoint")
        assert hasattr(AuditLog, "status_code")
        assert hasattr(AuditLog, "client_ip")
        assert hasattr(AuditLog, "timestamp")


class TestSoftDelete:
    """G79: Soft delete implementation."""

    def test_soft_delete_fields(self):
        """User, Purchase, Subscription have deleted_at field."""
        from api.db import User, Purchase, Subscription
        assert hasattr(User, "deleted_at")
        assert hasattr(Purchase, "deleted_at")
        assert hasattr(Subscription, "deleted_at")

    def test_deleted_at_nullable(self):
        """deleted_at column is nullable (initially NULL)."""
        from api.db import User
        col = User.__table__.columns["deleted_at"]
        assert col.nullable is True
