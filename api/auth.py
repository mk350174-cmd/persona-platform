"""
API key authentication middleware.

Every protected endpoint requires:
  Header: X-API-Key: prs_<56 hex chars>

Access rules:
  - /personas (GET)  → public
  - /v1/compile      → requires valid key + persona purchased
  - /checkout        → requires valid key
  - /me              → requires valid key
"""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from api.db import User, get_db, get_user_by_api_key, has_purchased


def _require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> str:
    if not x_api_key or not x_api_key.startswith("prs_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Header: X-API-Key: prs_...",
        )
    return x_api_key


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
