"""API Key management endpoints — rotation and revocation with grace period."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.db import User, APIKeyRotation, get_db, hash_api_key
from api.auth import get_current_user

# Grace period: old key remains valid for N days after rotation
API_KEY_GRACE_PERIOD_DAYS = 7

router = APIRouter(prefix="/me/api-keys", tags=["api-keys"])


class RotateKeyResponse(BaseModel):
    """Response when rotating API key."""

    new_api_key: str
    old_key_prefix: str
    message: str


class APIKeyInfo(BaseModel):
    """Information about an API key."""

    key_id: str
    key_preview: str
    created_at: datetime
    deprecated_at: datetime | None
    status: str  # "active" | "deprecated" | "revoked"


class APIKeyListResponse(BaseModel):
    """List of API keys for the user."""

    total: int
    keys: list[APIKeyInfo]


@router.post("/rotate", response_model=RotateKeyResponse)
def rotate_api_key(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Rotate API key: Generate new key, deprecate old key.
    New key is shown once — store it safely.
    Old key prefix remains valid for 7 days to allow client migration.
    """
    old_prefix = user.api_key  # Already a prefix after migration

    # Generate new key
    full_key = User.generate_api_key()
    new_prefix = full_key[:20]
    new_hash = hash_api_key(full_key)

    user.api_key = new_prefix
    user.api_key_hash = new_hash
    db.add(user)
    db.flush()

    # Log old key as deprecated (grace period tracking)
    now = datetime.now(timezone.utc)
    old_rotation = APIKeyRotation(
        user_id=user.id,
        api_key=old_prefix,
        deprecated_at=now,
        reason="rotation",
    )
    db.add(old_rotation)

    # Log new key
    new_rotation = APIKeyRotation(
        user_id=user.id,
        api_key=new_prefix,
        reason="rotation",
    )
    db.add(new_rotation)

    db.commit()

    grace_period_end = now + timedelta(days=API_KEY_GRACE_PERIOD_DAYS)

    return RotateKeyResponse(
        new_api_key=full_key,
        old_key_prefix=old_prefix,
        message=(
            f"API key rotated. Store the new key safely — it won't be shown again. "
            f"Old key prefix is deprecated but valid until {grace_period_end.strftime('%Y-%m-%d')} "
            f"({API_KEY_GRACE_PERIOD_DAYS}-day grace period). Update your clients before then."
        ),
    )


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific API key by ID and issue a replacement."""
    current_prefix = user.api_key
    if key_id != current_prefix[:8]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only revoke the current API key. Use /rotate to create a new one.",
        )

    # Mark current key as revoked
    current_rotation = APIKeyRotation(
        user_id=user.id,
        api_key=current_prefix,
        deprecated_at=datetime.now(timezone.utc),
        reason="revocation",
    )
    db.add(current_rotation)

    # Issue replacement
    full_key = User.generate_api_key()
    new_prefix = full_key[:20]
    user.api_key = new_prefix
    user.api_key_hash = hash_api_key(full_key)
    db.add(user)

    new_rotation = APIKeyRotation(
        user_id=user.id,
        api_key=new_prefix,
        reason="rotation",
    )
    db.add(new_rotation)
    db.commit()

    return {
        "status": "revoked",
        "new_api_key": full_key,
        "message": "Previous API key revoked. Store the new key safely.",
    }


@router.get("", response_model=APIKeyListResponse)
def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all API key entries (current and history) for the user."""
    rotations = db.query(APIKeyRotation).filter_by(user_id=user.id).order_by(
        APIKeyRotation.created_at.desc()
    ).all()

    keys = []
    for rotation in rotations:
        prefix = rotation.api_key
        key_preview = prefix[:8] + "..." + prefix[-4:] if len(prefix) >= 12 else prefix
        is_active = prefix == user.api_key
        status_str = (
            "active" if is_active
            else ("deprecated" if rotation.deprecated_at else "active")
        )
        keys.append(APIKeyInfo(
            key_id=rotation.id,
            key_preview=key_preview,
            created_at=rotation.created_at,
            deprecated_at=rotation.deprecated_at,
            status=status_str,
        ))

    return APIKeyListResponse(total=len(keys), keys=keys)
