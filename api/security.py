"""
Auth primitives: Argon2 password hashing, JWT issuance/verification, API key
generation. (T2-007/T2-009/T2-010 — auth scheme design, JWT/RBAC, API keys.)
"""

from __future__ import annotations

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt, JWTError

_ph = PasswordHasher()

# In production this MUST come from a secret manager, never a repo default.
# Test-mode default matches the pattern already used by legal/ drafts and
# ci.yml (sk_test_dummy) — a real deployment sets JWT_SECRET_KEY explicitly.
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24h


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: int, expires_minutes: int = JWT_EXPIRE_MINUTES) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Return the user id encoded in the token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, key_hash, key_preview). Only the hash is stored."""
    raw = "prs_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    preview = f"{raw[:8]}...{raw[-4:]}"
    return raw, key_hash, preview


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
