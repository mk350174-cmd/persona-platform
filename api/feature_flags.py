"""
Feature Flags Service — Server-side flag management and evaluation

Supports:
- Boolean flags (on/off)
- Percentage-based rollouts (10%, 50%, 100%)
- User targeting (specific users, segments)
- Variant allocation (A/B tests with multiple variants)
"""

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from api.db import FeatureFlag


class FlagEvaluationContext:
    """Context for evaluating a feature flag."""

    def __init__(
        self,
        user_id: str,
        user_email: str = "",
        user_tier: str = "free",
        segments: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize flag evaluation context."""
        self.user_id = user_id
        self.user_email = user_email
        self.user_tier = user_tier
        self.segments = segments or []
        self.metadata = metadata or {}


class FlagVariant(Enum):
    """Standard variant names for A/B tests."""

    CONTROL = "control"  # Original experience
    VARIANT_A = "variant_a"  # First variant
    VARIANT_B = "variant_b"  # Second variant
    VARIANT_C = "variant_c"  # Third variant


# ── Flag Evaluation ───────────────────────────────────────────────────────────


def _hash_user_id(user_id: str) -> int:
    """Deterministic hash of user ID for consistent variant allocation."""
    hash_obj = hashlib.md5(user_id.encode(), usedforsecurity=False)  # nosec B324
    return int(hash_obj.hexdigest(), 16) % 100  # 0-99


def evaluate_percentage_rollout(user_id: str, percentage: int) -> bool:
    """Evaluate if user is in percentage rollout (0-100)."""
    if percentage <= 0:
        return False
    if percentage >= 100:
        return True
    return _hash_user_id(user_id) < percentage


def evaluate_user_targeting(user_id: str, user_list: list[str]) -> bool:
    """Evaluate if user is in explicit user list."""
    return user_id in user_list


def evaluate_segment_targeting(segments: list[str], target_segments: list[str]) -> bool:
    """Evaluate if user is in any target segment."""
    if not target_segments:
        return True
    return any(seg in target_segments for seg in segments)


def evaluate_tier_targeting(user_tier: str, target_tiers: list[str]) -> bool:
    """Evaluate if user tier matches target tiers."""
    if not target_tiers:
        return True
    return user_tier in target_tiers


def get_variant_for_user(
    user_id: str,
    variants: list[str],
) -> str:
    """Get consistent variant allocation for user.

    Ensures same user always gets same variant (sticky allocation).
    """
    if not variants:
        return "control"
    if len(variants) == 1:
        return variants[0]

    user_hash = _hash_user_id(user_id)
    variant_index = user_hash % len(variants)
    return variants[variant_index]


def should_enable_flag(
    flag,  # FeatureFlag model
    context: FlagEvaluationContext,
) -> bool:
    """Evaluate if a feature flag should be enabled for a user.

    Returns True if:
    - Flag is enabled globally
    - User is in percentage rollout
    - User is explicitly targeted
    - User matches segment and tier filters
    """
    # Flag must be enabled
    if not flag.enabled:
        return False

    # Check expiration
    if flag.expires_at:
        now = datetime.now(timezone.utc)
        expires_at = flag.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            return False

    # Always enable for explicitly targeted users
    if context.user_id in flag.targeted_user_ids:
        return True

    # Check segment targeting
    if flag.target_segments:
        if not evaluate_segment_targeting(context.segments, flag.target_segments):
            return False

    # Check tier targeting
    if flag.target_tiers:
        if not evaluate_tier_targeting(context.user_tier, flag.target_tiers):
            return False

    # Check percentage rollout
    return evaluate_percentage_rollout(context.user_id, flag.rollout_percentage)


def get_flag_variant(
    flag,  # FeatureFlag model
    context: FlagEvaluationContext,
    db: Session,
) -> str | None:
    """Get variant for user if flag is enabled, else None.

    For A/B tests, returns variant name.
    For boolean flags, returns "enabled" or None.
    """
    if not should_enable_flag(flag, context):
        return None

    # If flag has variants, allocate one
    if flag.variants:
        variant = get_variant_for_user(context.user_id, flag.variants)
        # Log evaluation for analytics
        _log_flag_evaluation(db, flag.id, context.user_id, variant, True)
        return variant

    # Boolean flag enabled
    _log_flag_evaluation(db, flag.id, context.user_id, "enabled", True)
    return "enabled"


# ── Analytics Logging ─────────────────────────────────────────────────────────


def _log_flag_evaluation(
    db: Session,
    flag_id: str,
    user_id: str,
    variant: str,
    enabled: bool,
) -> None:
    """Log flag evaluation for analytics (async in production)."""
    from api.db import FlagEvaluation

    try:
        evaluation = FlagEvaluation(
            id=f"eval_{hashlib.md5(f'{flag_id}{user_id}{datetime.now().isoformat()}'.encode(), usedforsecurity=False).hexdigest()[:16]}",  # nosec B324
            flag_id=flag_id,
            user_id=user_id,
            variant=variant,
            enabled=enabled,
            evaluated_at=datetime.now(timezone.utc),
        )
        db.add(evaluation)
        db.commit()
    except Exception:
        # Don't let logging failures break flag evaluation
        db.rollback()


# ── Flag Management ───────────────────────────────────────────────────────────


def create_feature_flag(
    db: Session,
    name: str,
    description: str = "",
    enabled: bool = False,
    rollout_percentage: int = 0,
    variants: list[str] | None = None,
    target_user_ids: list[str] | None = None,
    target_segments: list[str] | None = None,
    target_tiers: list[str] | None = None,
    expires_at: datetime | None = None,
) -> "FeatureFlag":
    """Create a new feature flag."""
    from api.db import FeatureFlag
    import secrets

    flag = FeatureFlag(
        id=f"ff_{secrets.token_hex(8)}",
        name=name,
        description=description,
        enabled=enabled,
        rollout_percentage=rollout_percentage,
        variants=variants or [],
        targeted_user_ids=target_user_ids or [],
        target_segments=target_segments or [],
        target_tiers=target_tiers or [],
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag


def get_feature_flag(db: Session, flag_name: str) -> "FeatureFlag | None":
    """Get a feature flag by name."""
    from api.db import FeatureFlag

    return db.query(FeatureFlag).filter(FeatureFlag.name == flag_name).first()


def update_feature_flag(
    db: Session,
    flag_name: str,
    enabled: bool | None = None,
    rollout_percentage: int | None = None,
    target_user_ids: list[str] | None = None,
    target_segments: list[str] | None = None,
    target_tiers: list[str] | None = None,
    expires_at: datetime | None = None,
) -> "FeatureFlag | None":
    """Update an existing feature flag."""

    flag = get_feature_flag(db, flag_name)
    if not flag:
        return None

    if enabled is not None:
        flag.enabled = enabled
    if rollout_percentage is not None:
        flag.rollout_percentage = rollout_percentage
    if target_user_ids is not None:
        flag.targeted_user_ids = target_user_ids
    if target_segments is not None:
        flag.target_segments = target_segments
    if target_tiers is not None:
        flag.target_tiers = target_tiers
    if expires_at is not None:
        flag.expires_at = expires_at

    flag.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(flag)
    return flag


def delete_feature_flag(db: Session, flag_name: str) -> bool:
    """Delete a feature flag."""

    flag = get_feature_flag(db, flag_name)
    if flag:
        db.delete(flag)
        db.commit()
        return True
    return False


def list_feature_flags(db: Session, enabled_only: bool = False) -> list["FeatureFlag"]:
    """List all feature flags."""
    from api.db import FeatureFlag

    query = db.query(FeatureFlag)
    if enabled_only:
        query = query.filter(FeatureFlag.enabled == True)
    return query.all()


def get_flag_stats(db: Session, flag_id: str, hours: int = 24) -> dict:
    """Get evaluation statistics for a flag (enabled/disabled ratio)."""
    from api.db import FlagEvaluation
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    evals = db.query(FlagEvaluation).filter(
        FlagEvaluation.flag_id == flag_id,
        FlagEvaluation.evaluated_at >= cutoff,
    ).all()

    if not evals:
        return {"total": 0, "enabled": 0, "disabled": 0, "variants": {}}

    enabled = sum(1 for e in evals if e.enabled)
    disabled = len(evals) - enabled
    variants = {}
    for e in evals:
        if e.variant not in variants:
            variants[e.variant] = 0
        variants[e.variant] += 1

    return {
        "total": len(evals),
        "enabled": enabled,
        "disabled": disabled,
        "enabled_percent": round(100 * enabled / len(evals), 1),
        "variants": variants,
    }
