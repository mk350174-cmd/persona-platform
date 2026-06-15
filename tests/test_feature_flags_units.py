"""
Unit tests for api/feature_flags.py — flag evaluation + CRUD.

Pure evaluation functions need no DB; CRUD / stats use the `test_db` fixture
(file-based SQLite from conftest).
"""

from datetime import datetime, timezone, timedelta

import pytest

from api.feature_flags import (
    FlagEvaluationContext,
    FlagVariant,
    _hash_user_id,
    evaluate_percentage_rollout,
    evaluate_user_targeting,
    evaluate_segment_targeting,
    evaluate_tier_targeting,
    get_variant_for_user,
    should_enable_flag,
    get_flag_variant,
    create_feature_flag,
    get_feature_flag,
    update_feature_flag,
    delete_feature_flag,
    list_feature_flags,
    get_flag_stats,
)


# ── pure evaluation ──────────────────────────────────────────────────────────

def test_hash_user_id_deterministic_and_bounded():
    a = _hash_user_id("user_42")
    b = _hash_user_id("user_42")
    assert a == b
    assert 0 <= a < 100


def test_percentage_rollout_edges():
    assert evaluate_percentage_rollout("u", 0) is False
    assert evaluate_percentage_rollout("u", -5) is False
    assert evaluate_percentage_rollout("u", 100) is True
    assert evaluate_percentage_rollout("u", 200) is True


def test_percentage_rollout_is_sticky():
    # same user, same percentage → same answer every time
    results = {evaluate_percentage_rollout("steady_user", 50) for _ in range(5)}
    assert len(results) == 1


def test_user_targeting():
    assert evaluate_user_targeting("u1", ["u1", "u2"]) is True
    assert evaluate_user_targeting("u3", ["u1", "u2"]) is False


def test_segment_targeting_empty_target_matches_all():
    assert evaluate_segment_targeting(["beta"], []) is True
    assert evaluate_segment_targeting(["beta"], ["beta", "pro"]) is True
    assert evaluate_segment_targeting(["free"], ["beta", "pro"]) is False


def test_tier_targeting_empty_target_matches_all():
    assert evaluate_tier_targeting("free", []) is True
    assert evaluate_tier_targeting("pro", ["pro", "enterprise"]) is True
    assert evaluate_tier_targeting("free", ["pro"]) is False


def test_get_variant_for_user():
    assert get_variant_for_user("u", []) == "control"
    assert get_variant_for_user("u", ["only"]) == "only"
    variants = ["control", "a", "b"]
    v = get_variant_for_user("u", variants)
    assert v in variants
    # sticky
    assert get_variant_for_user("u", variants) == v


def test_flag_variant_enum_values():
    assert FlagVariant.CONTROL.value == "control"
    assert FlagVariant.VARIANT_A.value == "variant_a"


# ── should_enable_flag (needs a flag-like object) ────────────────────────────

class _Flag:
    """Lightweight stand-in for the FeatureFlag model."""
    def __init__(self, **kw):
        self.enabled = kw.get("enabled", True)
        self.expires_at = kw.get("expires_at")
        self.targeted_user_ids = kw.get("targeted_user_ids", [])
        self.target_segments = kw.get("target_segments", [])
        self.target_tiers = kw.get("target_tiers", [])
        self.rollout_percentage = kw.get("rollout_percentage", 100)
        self.variants = kw.get("variants", [])
        self.id = kw.get("id", "ff_test")


def test_should_enable_disabled_flag():
    ctx = FlagEvaluationContext("u")
    assert should_enable_flag(_Flag(enabled=False), ctx) is False


def test_should_enable_expired_flag():
    ctx = FlagEvaluationContext("u")
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    assert should_enable_flag(_Flag(expires_at=past), ctx) is False


def test_should_enable_naive_expiry_treated_as_utc():
    ctx = FlagEvaluationContext("u")
    future_naive = datetime.now() + timedelta(hours=1)  # naive
    assert should_enable_flag(_Flag(expires_at=future_naive, rollout_percentage=100), ctx) is True


def test_should_enable_targeted_user_always_on():
    ctx = FlagEvaluationContext("vip")
    assert should_enable_flag(_Flag(targeted_user_ids=["vip"], rollout_percentage=0), ctx) is True


def test_should_enable_segment_and_tier_filters():
    ctx = FlagEvaluationContext("u", user_tier="pro", segments=["beta"])
    assert should_enable_flag(_Flag(target_segments=["beta"], target_tiers=["pro"]), ctx) is True
    # wrong tier
    ctx2 = FlagEvaluationContext("u", user_tier="free", segments=["beta"])
    assert should_enable_flag(_Flag(target_segments=["beta"], target_tiers=["pro"]), ctx2) is False
    # wrong segment
    ctx3 = FlagEvaluationContext("u", user_tier="pro", segments=["alpha"])
    assert should_enable_flag(_Flag(target_segments=["beta"]), ctx3) is False


def test_should_enable_percentage_zero_blocks():
    ctx = FlagEvaluationContext("u")
    assert should_enable_flag(_Flag(rollout_percentage=0), ctx) is False


# ── get_flag_variant (logs to DB) ────────────────────────────────────────────

def test_get_flag_variant_boolean_enabled(test_db):
    ctx = FlagEvaluationContext("u")
    assert get_flag_variant(_Flag(rollout_percentage=100), ctx, test_db) == "enabled"


def test_get_flag_variant_disabled_returns_none(test_db):
    ctx = FlagEvaluationContext("u")
    assert get_flag_variant(_Flag(enabled=False), ctx, test_db) is None


def test_get_flag_variant_ab_allocates(test_db):
    ctx = FlagEvaluationContext("u")
    v = get_flag_variant(_Flag(rollout_percentage=100, variants=["control", "a"]), ctx, test_db)
    assert v in ("control", "a")


# ── CRUD + stats (test_db) ───────────────────────────────────────────────────

def test_create_get_update_delete_flag(test_db):
    flag = create_feature_flag(test_db, "new_ui", description="rollout", enabled=True,
                               rollout_percentage=25, variants=["control", "a"])
    assert flag.name == "new_ui" and flag.enabled is True

    fetched = get_feature_flag(test_db, "new_ui")
    assert fetched is not None and fetched.rollout_percentage == 25

    updated = update_feature_flag(test_db, "new_ui", enabled=False, rollout_percentage=50,
                                  target_tiers=["pro"])
    assert updated.enabled is False and updated.rollout_percentage == 50
    assert updated.target_tiers == ["pro"]

    assert delete_feature_flag(test_db, "new_ui") is True
    assert get_feature_flag(test_db, "new_ui") is None


def test_update_missing_flag_returns_none(test_db):
    assert update_feature_flag(test_db, "ghost", enabled=True) is None


def test_delete_missing_flag_returns_false(test_db):
    assert delete_feature_flag(test_db, "ghost") is False


def test_list_feature_flags_enabled_filter(test_db):
    create_feature_flag(test_db, "on_flag", enabled=True)
    create_feature_flag(test_db, "off_flag", enabled=False)
    all_flags = list_feature_flags(test_db)
    assert {f.name for f in all_flags} >= {"on_flag", "off_flag"}
    enabled = list_feature_flags(test_db, enabled_only=True)
    names = {f.name for f in enabled}
    assert "on_flag" in names and "off_flag" not in names


def test_get_flag_stats_empty(test_db):
    flag = create_feature_flag(test_db, "stat_flag", enabled=True, rollout_percentage=100)
    stats = get_flag_stats(test_db, flag.id)
    assert stats == {"total": 0, "enabled": 0, "disabled": 0, "variants": {}}


def test_get_flag_stats_after_evaluations(test_db):
    flag = create_feature_flag(test_db, "ab_flag", enabled=True, rollout_percentage=100,
                               variants=["control", "a"])
    ctx = FlagEvaluationContext("user_one")
    get_flag_variant(flag, ctx, test_db)
    get_flag_variant(flag, FlagEvaluationContext("user_two"), test_db)
    stats = get_flag_stats(test_db, flag.id)
    assert stats["total"] == 2
    assert stats["enabled"] == 2
    assert stats["enabled_percent"] == 100.0
    assert sum(stats["variants"].values()) == 2
