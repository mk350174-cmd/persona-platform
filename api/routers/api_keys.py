"""API Key management endpoints — rotation and revocation."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.db import User, APIKeyRotation, get_db
from api.auth import get_current_user

router = APIRouter(prefix="/me/api-keys", tags=["api-keys"])


class RotateKeyResponse(BaseModel):
    """Response when rotating API key."""

    new_api_key: str
    old_api_key_deprecated: str
    message: str


class APIKeyInfo(BaseModel):
    """Information about an API key."""

    key_id: str
    key_preview: str  # First 8 chars + last 4 chars
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
    Old key remains valid for grace period (7 days) before expiration.
    """
    old_key = user.api_key

    # Generate new key
    new_key = User.generate_api_key()
    user.api_key = new_key
    db.add(user)
    db.flush()

    # Log old key as deprecated in rotation history
    old_rotation = APIKeyRotation(
        user_id=user.id,
        api_key=old_key,
        deprecated_at=datetime.now(timezone.utc),
        reason="rotation",
    )
    db.add(old_rotation)

    # Log new key in rotation history
    new_rotation = APIKeyRotation(
        user_id=user.id,
        api_key=new_key,
        reason="rotation",
    )
    db.add(new_rotation)

    db.commit()

    return RotateKeyResponse(
        new_api_key=new_key,
        old_api_key_deprecated=old_key,
        message=(
            "API key rotated successfully. Old key is deprecated but still valid. "
            "Update your clients within 7 days."
        ),
    )


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke a specific API key by ID.
    Note: Currently only supports revoking the current key.
    """
    # For MVP, only allow revoking the current key
    if key_id != user.api_key[:8]:  # Compare preview (first 8 chars)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only revoke the current API key. Use /rotate to create a new one.",
        )

    # Mark current key as revoked in history
    current_rotation = APIKeyRotation(
        user_id=user.id,
        api_key=user.api_key,
        deprecated_at=datetime.now(timezone.utc),
        reason="revocation",
    )
    db.add(current_rotation)

    # Generate and assign new key
    new_key = User.generate_api_key()
    user.api_key = new_key
    db.add(user)

    # Log new key
    new_rotation = APIKeyRotation(
        user_id=user.id,
        api_key=new_key,
        reason="rotation",  # After revocation
    )
    db.add(new_rotation)

    db.commit()

    return {
        "status": "revoked",
        "new_api_key": new_key,
        "message": "Previous API key revoked. New key generated.",
    }


@router.get("", response_model=APIKeyListResponse)
def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys (current and history) for the user.
    Shows creation date, deprecation date, and status.
    """
    rotations = db.query(APIKeyRotation).filter_by(user_id=user.id).order_by(
        APIKeyRotation.created_at.desc()
    ).all()

    keys = []
    for rotation in rotations:
        key_preview = rotation.api_key[:8] + "..." + rotation.api_key[-4:]
        status_str = (
            "active"
            if rotation.api_key == user.api_key
            else ("deprecated" if rotation.deprecated_at else "revoked")
        )

        keys.append(
            APIKeyInfo(
                key_id=rotation.id,
                key_preview=key_preview,
                created_at=rotation.created_at,
                deprecated_at=rotation.deprecated_at,
                status=status_str,
            )
        )

    return APIKeyListResponse(total=len(keys), keys=keys)
