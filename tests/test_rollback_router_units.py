"""
Unit tests for api/routers/rollback.py — called as plain functions.

These endpoints are synchronous and depend only on (user, db), so we invoke them
directly with a fake admin user and a seeded `test_db` (no HTTP/auth layer needed).
"""

import pytest
from fastapi import HTTPException

from api.routers import rollback as rb
from api.db import RollbackPolicy as RollbackPolicyModel, create_user
from api.rollback import RollbackStatus


def _policy(test_db, enabled=True, require_approval=False):
    p = RollbackPolicyModel(
        enabled=enabled, error_rate_threshold_percent=2, latency_threshold_ms=500,
        window_minutes=5, min_samples=100, cooldown_minutes=0,
        require_approval=require_approval, max_rollbacks_per_hour=3,
    )
    test_db.add(p)
    test_db.commit()
    test_db.refresh(p)
    return p


def _user(test_db):
    u, _ = create_user(test_db, "admin@rb.com")
    u.role = "admin"
    test_db.commit()
    return u


# ── policy GET/PATCH ─────────────────────────────────────────────────────────

def test_get_policy_404_when_missing(test_db):
    with pytest.raises(HTTPException) as ei:
        rb.get_rollback_policy(user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


def test_get_policy_returns_config(test_db):
    _policy(test_db)
    out = rb.get_rollback_policy(user=_user(test_db), db=test_db)
    assert out["enabled"] is True
    assert out["max_rollbacks_per_hour"] == 3


def test_update_policy(test_db):
    _policy(test_db)
    out = rb.update_rollback_policy(enabled=False, error_rate_threshold_percent=5.0,
                                    user=_user(test_db), db=test_db)
    assert out["enabled"] is False
    assert out["error_rate_threshold_percent"] == 5.0


def test_update_policy_404(test_db):
    with pytest.raises(HTTPException) as ei:
        rb.update_rollback_policy(enabled=True, user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


# ── evaluate ─────────────────────────────────────────────────────────────────

def test_evaluate_requires_policy(test_db):
    with pytest.raises(HTTPException) as ei:
        rb.evaluate_rollback("2.0", "1.0", 10.0, 1.0, 900.0, 100.0,
                             user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


def test_evaluate_triggers_rollback(test_db):
    _policy(test_db)
    out = rb.evaluate_rollback("2.0", "1.0", error_rate_current=10.0, error_rate_baseline=1.0,
                               latency_current_ms=900.0, latency_baseline_ms=100.0,
                               sample_count=200, critical_errors=["boom"],
                               user=_user(test_db), db=test_db)
    assert out["should_rollback"] is True
    assert out["alert"] is not None


def test_evaluate_stable_no_rollback(test_db):
    _policy(test_db)
    out = rb.evaluate_rollback("2.0", "1.0", 0.1, 0.1, 100.0, 100.0,
                               sample_count=200, user=_user(test_db), db=test_db)
    assert out["should_rollback"] is False
    assert out["alert"] is None


# ── execute ──────────────────────────────────────────────────────────────────

def test_execute_disabled_policy(test_db):
    _policy(test_db, enabled=False)
    with pytest.raises(HTTPException) as ei:
        rb.execute_rollback("2.0", "1.0", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 403


def test_execute_invalid_reason(test_db):
    _policy(test_db)
    with pytest.raises(HTTPException) as ei:
        rb.execute_rollback("2.0", "1.0", reason="banana", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 400


def test_execute_in_progress(test_db):
    _policy(test_db, require_approval=False)
    out = rb.execute_rollback("2.0", "1.0", reason="error_rate_spike",
                              user=_user(test_db), db=test_db)
    assert out["status"] == "in_progress"
    assert out["rollback_id"]


def test_execute_pending_approval(test_db):
    _policy(test_db, require_approval=True)
    out = rb.execute_rollback("2.0", "1.0", user=_user(test_db), db=test_db)
    assert out["status"] == "pending_approval"


# ── completion + history + approve ───────────────────────────────────────────

def test_record_completion_and_history(test_db):
    _policy(test_db)
    user = _user(test_db)
    ex = rb.execute_rollback("2.0", "1.0", user=user, db=test_db)
    rid = ex["rollback_id"]
    done = rb.record_rollback_completion(rid, "completed", user=user, db=test_db)
    assert done["status"] == "completed"
    hist = rb.get_rollback_history_endpoint(user=user, db=test_db)
    assert hist["total"] >= 1


def test_record_completion_invalid_status(test_db):
    with pytest.raises(HTTPException) as ei:
        rb.record_rollback_completion("x", "weird", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 400


def test_record_completion_missing(test_db):
    with pytest.raises(HTTPException) as ei:
        rb.record_rollback_completion("ghost", "completed", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


def test_approve_flow(test_db):
    _policy(test_db, require_approval=True)
    user = _user(test_db)
    ex = rb.execute_rollback("2.0", "1.0", approval_token="tok123", user=user, db=test_db)
    rid = ex["rollback_id"]
    out = rb.approve_rollback(rid, "tok123", user=user, db=test_db)
    assert out["status"] == "in_progress"


def test_approve_missing(test_db):
    with pytest.raises(HTTPException) as ei:
        rb.approve_rollback("ghost", "tok", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


def test_approve_wrong_token(test_db):
    _policy(test_db, require_approval=True)
    user = _user(test_db)
    ex = rb.execute_rollback("2.0", "1.0", approval_token="right", user=user, db=test_db)
    with pytest.raises(HTTPException) as ei:
        rb.approve_rollback(ex["rollback_id"], "wrong", user=user, db=test_db)
    assert ei.value.status_code == 403
