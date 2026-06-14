"""
Unit tests for api/rollback.py — spike detection + rollback decision engine.

Pure decision logic needs no DB; cooldown/history persistence use `test_db`.
"""

from datetime import datetime, timezone

import pytest

from api.rollback import (
    RollbackReason,
    RollbackStatus,
    RollbackPolicy,
    DeploymentVersion,
    RollbackContext,
    detect_error_rate_spike,
    detect_latency_spike,
    evaluate_rollback_decision,
    _get_rollback_action,
    can_rollback_now,
    record_rollback,
    update_rollback_status,
    get_rollback_history,
    format_rollback_alert,
    get_previous_stable_version,
)


# ── spike detection ──────────────────────────────────────────────────────────

def test_error_rate_spike_from_zero_baseline():
    is_spike, pct = detect_error_rate_spike(0.5, 0.0)
    assert is_spike is True and pct == float("inf")
    # below 0.1 with zero baseline → not a spike
    assert detect_error_rate_spike(0.05, 0.0)[0] is False


def test_error_rate_spike_threshold():
    # 1% → 3% is +200% ≥ 150% default
    is_spike, pct = detect_error_rate_spike(3.0, 1.0)
    assert is_spike is True
    assert pct == pytest.approx(200.0)
    # +50% < 150% → not a spike
    assert detect_error_rate_spike(1.5, 1.0)[0] is False


def test_latency_spike_from_zero_baseline():
    assert detect_latency_spike(200.0, 0.0)[0] is True
    assert detect_latency_spike(50.0, 0.0)[0] is False


def test_latency_spike_threshold():
    is_spike, pct = detect_latency_spike(160.0, 100.0)   # +60% ≥ 50%
    assert is_spike is True and pct == pytest.approx(60.0)
    assert detect_latency_spike(120.0, 100.0)[0] is False  # +20%


# ── evaluate_rollback_decision ───────────────────────────────────────────────

def _ver(tag="1.0.0"):
    return DeploymentVersion(version=tag, image_uri=f"img:{tag}",
                             deployed_at=datetime.now(timezone.utc),
                             is_stable=True, can_rollback_to=True)


def _ctx(**kw):
    defaults = dict(
        current_version=_ver("2.0.0"), previous_version=_ver("1.0.0"),
        error_rate_current=0.1, error_rate_baseline=0.1,
        latency_current_ms=100.0, latency_baseline_ms=100.0,
        error_count=0, sample_count=200, critical_errors=[],
        reason=RollbackReason.ERROR_RATE_SPIKE,
    )
    defaults.update(kw)
    return RollbackContext(**defaults)


def _policy(**kw):
    defaults = dict(enabled=True, error_rate_threshold_percent=2.0, latency_threshold_ms=500,
                    window_minutes=5, min_samples=100, cooldown_minutes=15,
                    require_approval=False, max_rollbacks_per_hour=3)
    defaults.update(kw)
    return RollbackPolicy(**defaults)


def test_decision_stable_no_rollback():
    d = evaluate_rollback_decision(_ctx(), _policy())
    assert d.should_rollback is False
    assert d.severity == "low"
    assert d.recommended_action == "Continue monitoring"


def test_decision_error_spike_triggers_rollback():
    ctx = _ctx(error_rate_current=10.0, error_rate_baseline=1.0)   # +900%, above 2% threshold
    d = evaluate_rollback_decision(ctx, _policy())
    assert d.should_rollback is True
    assert d.severity == "critical"
    assert d.confidence > 0
    assert "Error rate spiked" in d.explanation


def test_decision_critical_errors_trigger():
    ctx = _ctx(critical_errors=["OOMKilled", "SegFault"])
    d = evaluate_rollback_decision(ctx, _policy())
    assert d.should_rollback is True
    assert d.severity == "critical"


def test_decision_latency_only_is_high():
    ctx = _ctx(latency_current_ms=900.0, latency_baseline_ms=100.0)   # +800%, above 500ms
    d = evaluate_rollback_decision(ctx, _policy())
    assert d.should_rollback is True
    assert d.severity == "high"


def test_decision_insufficient_samples_blocks():
    # error spike present but sample_count below min_samples → negative score blocks rollback
    ctx = _ctx(error_rate_current=10.0, error_rate_baseline=1.0, sample_count=5)
    d = evaluate_rollback_decision(ctx, _policy(min_samples=100))
    assert d.should_rollback is False


def test_get_rollback_action_levels():
    assert "URGENT" in _get_rollback_action("critical")
    assert "approval" in _get_rollback_action("high")
    assert "monitor" in _get_rollback_action("medium").lower()


# ── format_rollback_alert ────────────────────────────────────────────────────

def test_format_rollback_alert_shape():
    d = evaluate_rollback_decision(_ctx(critical_errors=["boom"]), _policy())
    alert = format_rollback_alert(d, "2.0.0", "1.0.0")
    assert alert["from_version"] == "2.0.0"
    assert alert["to_version"] == "1.0.0"
    assert alert["severity"] == "CRITICAL"
    assert "manual_rollback_command" in alert


# ── DB-backed: cooldown + history ────────────────────────────────────────────

def test_can_rollback_now_when_empty(test_db):
    ok, reason = can_rollback_now(test_db, _policy())
    assert ok is True and reason is None


def test_record_and_history(test_db):
    rb = record_rollback(test_db, "2.0.0", "1.0.0", RollbackReason.ERROR_RATE_SPIKE)
    assert rb.status == RollbackStatus.PENDING.value
    hist = get_rollback_history(test_db)
    assert len(hist) == 1 and hist[0].from_version == "2.0.0"


def test_update_status_completed_sets_timestamp(test_db):
    rb = record_rollback(test_db, "2.0.0", "1.0.0", RollbackReason.MANUAL_TRIGGER)
    updated = update_rollback_status(test_db, rb.id, RollbackStatus.COMPLETED,
                                     details={"note": "done"})
    assert updated.status == RollbackStatus.COMPLETED.value
    assert updated.completed_at is not None
    assert updated.details["note"] == "done"


def test_update_status_missing_returns_none(test_db):
    assert update_rollback_status(test_db, "nope", RollbackStatus.FAILED) is None


def test_cooldown_blocks_after_recent_completed(test_db):
    rb = record_rollback(test_db, "2.0.0", "1.0.0", RollbackReason.CRITICAL_ERROR)
    update_rollback_status(test_db, rb.id, RollbackStatus.COMPLETED)
    ok, reason = can_rollback_now(test_db, _policy(cooldown_minutes=15))
    assert ok is False and "cooldown" in reason


def test_max_rollbacks_per_hour(test_db):
    for _ in range(3):
        rb = record_rollback(test_db, "2.0.0", "1.0.0", RollbackReason.CRITICAL_ERROR)
        update_rollback_status(test_db, rb.id, RollbackStatus.COMPLETED)
    ok, reason = can_rollback_now(test_db, _policy(cooldown_minutes=0, max_rollbacks_per_hour=3))
    assert ok is False and "Max rollbacks" in reason


def test_get_previous_stable_version(test_db):
    assert get_previous_stable_version(test_db) is None
    rb = record_rollback(test_db, "2.0.0", "1.5.0", RollbackReason.MANUAL_TRIGGER)
    update_rollback_status(test_db, rb.id, RollbackStatus.COMPLETED)
    assert get_previous_stable_version(test_db) == "1.5.0"
