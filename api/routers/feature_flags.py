"""Feature Flags API — Server-side feature management and A/B testing."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from api.db import get_db, User, FeatureFlag
from api.auth import get_current_user
from api.feature_flags import (
    create_feature_flag,
    get_feature_flag,
    update_feature_flag,
    delete_feature_flag,
    list_feature_flags,
    get_flag_stats,
    FlagEvaluationContext,
    should_enable_flag,
    get_flag_variant,
)

router = APIRouter(prefix="/flags", tags=["feature-flags"])


# ── Models ────────────────────────────────────────────────────────────────────

class CreateFlagRequest:
    """Request to create a feature flag."""

    def __init__(
        self,
        name: str,
        description: str = "",
        enabled: bool = False,
        rollout_percentage: int = 0,
        variants: Optional[list[str]] = None,
        target_user_ids: Optional[list[str]] = None,
        target_segments: Optional[list[str]] = None,
        target_tiers: Optional[list[str]] = None,
        expires_at: Optional[datetime] = None,
    ):
        self.name = name
        self.description = description
        self.enabled = enabled
        self.rollout_percentage = rollout_percentage
        self.variants = variants or []
        self.target_user_ids = target_user_ids or []
        self.target_segments = target_segments or []
        self.target_tiers = target_tiers or []
        self.expires_at = expires_at


class UpdateFlagRequest:
    """Request to update a feature flag."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        rollout_percentage: Optional[int] = None,
        target_user_ids: Optional[list[str]] = None,
        target_segments: Optional[list[str]] = None,
        target_tiers: Optional[list[str]] = None,
        expires_at: Optional[datetime] = None,
    ):
        self.enabled = enabled
        self.rollout_percentage = rollout_percentage
        self.target_user_ids = target_user_ids
        self.target_segments = target_segments
        self.target_tiers = target_tiers
        self.expires_at = expires_at


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
def list_flags(
    enabled_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all feature flags (admin access may be required in production)."""
    flags = list_feature_flags(db, enabled_only=enabled_only)
    return {
        "flags": [
            {
                "id": f.id,
                "name": f.name,
                "description": f.description,
                "enabled": f.enabled,
                "rollout_percentage": f.rollout_percentage,
                "variants": f.variants,
                "target_user_ids": f.targeted_user_ids,
                "target_segments": f.target_segments,
                "target_tiers": f.target_tiers,
                "expires_at": f.expires_at,
                "created_at": f.created_at,
                "updated_at": f.updated_at,
            }
            for f in flags
        ],
        "total": len(flags),
    }


@router.get("/{flag_name}")
def get_flag(
    flag_name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single feature flag by name."""
    flag = get_feature_flag(db, flag_name)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    return {
        "id": flag.id,
        "name": flag.name,
        "description": flag.description,
        "enabled": flag.enabled,
        "rollout_percentage": flag.rollout_percentage,
        "variants": flag.variants,
        "target_user_ids": flag.targeted_user_ids,
        "target_segments": flag.target_segments,
        "target_tiers": flag.target_tiers,
        "expires_at": flag.expires_at,
        "created_at": flag.created_at,
        "updated_at": flag.updated_at,
    }


@router.get("/{flag_name}/stats")
def get_flag_statistics(
    flag_name: str,
    hours: int = 24,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get statistics for a feature flag (enabled/disabled ratio, variant distribution)."""
    flag = get_feature_flag(db, flag_name)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    stats = get_flag_stats(db, flag.id, hours=hours)
    return {
        "flag_name": flag_name,
        "period_hours": hours,
        **stats,
    }


@router.post("/")
def create_flag(
    name: str,
    description: str = "",
    enabled: bool = False,
    rollout_percentage: int = 0,
    variants: Optional[list[str]] = None,
    target_user_ids: Optional[list[str]] = None,
    target_segments: Optional[list[str]] = None,
    target_tiers: Optional[list[str]] = None,
    expires_at: Optional[datetime] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new feature flag (admin access may be required in production)."""
    # Check if flag already exists
    existing = get_feature_flag(db, name)
    if existing:
        raise HTTPException(status_code=409, detail="Flag with this name already exists")

    flag = create_feature_flag(
        db,
        name=name,
        description=description,
        enabled=enabled,
        rollout_percentage=rollout_percentage,
        variants=variants,
        target_user_ids=target_user_ids,
        target_segments=target_segments,
        target_tiers=target_tiers,
        expires_at=expires_at,
    )

    return {
        "id": flag.id,
        "name": flag.name,
        "description": flag.description,
        "enabled": flag.enabled,
        "rollout_percentage": flag.rollout_percentage,
        "variants": flag.variants,
        "target_user_ids": flag.targeted_user_ids,
        "target_segments": flag.target_segments,
        "target_tiers": flag.target_tiers,
        "expires_at": flag.expires_at,
        "created_at": flag.created_at,
        "updated_at": flag.updated_at,
        "message": "Feature flag created successfully",
    }


@router.patch("/{flag_name}")
def update_flag(
    flag_name: str,
    enabled: Optional[bool] = None,
    rollout_percentage: Optional[int] = None,
    target_user_ids: Optional[list[str]] = None,
    target_segments: Optional[list[str]] = None,
    target_tiers: Optional[list[str]] = None,
    expires_at: Optional[datetime] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing feature flag (admin access may be required in production)."""
    flag = update_feature_flag(
        db,
        flag_name=flag_name,
        enabled=enabled,
        rollout_percentage=rollout_percentage,
        target_user_ids=target_user_ids,
        target_segments=target_segments,
        target_tiers=target_tiers,
        expires_at=expires_at,
    )

    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    return {
        "id": flag.id,
        "name": flag.name,
        "description": flag.description,
        "enabled": flag.enabled,
        "rollout_percentage": flag.rollout_percentage,
        "variants": flag.variants,
        "target_user_ids": flag.targeted_user_ids,
        "target_segments": flag.target_segments,
        "target_tiers": flag.target_tiers,
        "expires_at": flag.expires_at,
        "created_at": flag.created_at,
        "updated_at": flag.updated_at,
        "message": "Feature flag updated successfully",
    }


@router.delete("/{flag_name}")
def delete_flag(
    flag_name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a feature flag (admin access may be required in production)."""
    if not delete_feature_flag(db, flag_name):
        raise HTTPException(status_code=404, detail="Flag not found")

    return {
        "message": f"Feature flag '{flag_name}' deleted successfully",
    }


@router.post("/{flag_name}/evaluate")
def evaluate_flag(
    flag_name: str,
    segments: Optional[list[str]] = None,
    tier: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate a feature flag for the current user (client-side flag evaluation)."""
    flag = get_feature_flag(db, flag_name)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    context = FlagEvaluationContext(
        user_id=user.id,
        user_email=user.email,
        user_tier=tier or "free",
        segments=segments or [],
    )

    variant = get_flag_variant(flag, context, db)
    enabled = variant is not None

    return {
        "flag_name": flag_name,
        "user_id": user.id,
        "enabled": enabled,
        "variant": variant,
        "context": {
            "segments": context.segments,
            "tier": context.user_tier,
        },
    }
