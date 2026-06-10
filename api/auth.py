"""
API key and password authentication.

API Key:
  Header: X-API-Key: prs_<56 hex chars>
  or Authorization: Bearer prs_...

Password Login:
  POST /auth/login with {email, password}
  Returns API key on success

Access rules:
  - /personas (GET)  → public
  - /v1/compile      → requires valid key + persona purchased
  - /checkout        → requires valid key
  - /me              → requires valid key
"""

from typing import Optional
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status, Request
from sqlalchemy.orm import Session

from api.db import (
    User, get_db, get_user_by_api_key, has_purchased,
    verify_password, record_login_attempt, check_lockout, clear_login_attempts,
)


def _require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """
    Extract API key from either:
    1. X-API-Key header: X-API-Key: prs_...
    2. Authorization header: Authorization: Bearer prs_...
    """
    api_key = None

    # Try Authorization header first (Bearer format)
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].startswith("prs_"):
            api_key = parts[1]

    # Fall back to X-API-Key header
    if not api_key and x_api_key and x_api_key.startswith("prs_"):
        api_key = x_api_key

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Use: Authorization: Bearer prs_... or X-API-Key: prs_...",
        )

    return api_key


def get_current_user(
    api_key: str = Depends(_require_api_key),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: resolve API key → User or 401."""
    user = get_user_by_api_key(db, api_key)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key not found or inactive.",
        )
    return user


def require_persona_access(
    persona_id: str,
    user: User,
    db: Session,
) -> None:
    """
    Raise 403 if user has not purchased persona_id.

    Free tier personas (price_usd == 0) skip this check.
    """
    from api.catalog import PERSONA_CATALOG

    meta = PERSONA_CATALOG.get(persona_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")

    price = meta.get("price_usd", 0)
    if price == 0:
        return  # free persona — no purchase needed

    if not has_purchased(db, user.id, persona_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Persona '{persona_id}' requires purchase. "
                f"POST /checkout/{persona_id} to buy for ${price:.0f}."
            ),
        )


def authenticate_password(
    db: Session,
    email: str,
    password: str,
    client_ip: str,
) -> User:
    """
    Authenticate user by email + password.
    Track failed attempts and enforce lockout (5 attempts → 5 min lockout).
    Raises HTTPException on failure.
    """
    user = db.query(User).filter(User.email == email, User.deleted_at == None).first()

    # Check lockout before verifying password (prevent timing attack)
    if user and check_lockout(user):
        record_login_attempt(db, user.id, client_ip, success=False)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked. Please try again in a few minutes.",
        )

    # Constant-time check: always hash even if user not found (prevent user enumeration)
    if user and user.password_hash and verify_password(user.password_hash, password):
        record_login_attempt(db, user.id, client_ip, success=True)
        clear_login_attempts(db, user.id)
        if not user.active or user.deleted_at:
            raise HTTPException(status_code=401, detail="Account inactive or deleted.")
        return user

    # Log failed attempt even if user not found (timing attack: always hash dummy)
    if user:
        record_login_attempt(db, user.id, client_ip, success=False)
    else:
        # User not found: still hash a dummy password to avoid timing attack
        from api.db import hash_password
        hash_password(password)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )
