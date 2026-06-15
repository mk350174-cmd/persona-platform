"""
Unit tests for api/routers/performance.py — called as plain functions.

Synchronous endpoints depending only on (user, db) are invoked directly with a
fake user and a seeded `test_db`.
"""

import pytest
from fastapi import HTTPException

from api.routers import performance as perf
from api.performance_metrics import MetricType, record_metric, create_baseline
from api.db import create_user


def _user(test_db):
    u, _ = create_user(test_db, "perf@router.com")
    u.role = "admin"
    test_db.commit()
    return u


def _seed_metrics(test_db, n=12, value=115, endpoint=None):
    for _ in range(n):
        record_metric(test_db, MetricType.RESPONSE_TIME, value, endpoint=endpoint)


# ── list_metrics ─────────────────────────────────────────────────────────────

def test_list_metrics_requires_type(test_db):
    with pytest.raises(HTTPException) as ei:
        perf.list_metrics(user=_user(test_db), db=test_db)
    assert ei.value.status_code == 400


def test_list_metrics_invalid_type(test_db):
    with pytest.raises(HTTPException) as ei:
        perf.list_metrics(metric_type="banana", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 400


def test_list_metrics_ok(test_db):
    user = _user(test_db)
    _seed_metrics(test_db, n=3)
    out = perf.list_metrics(metric_type="response_time_ms", hours=1, user=user, db=test_db)
    assert out["count"] == 3


# ── record ───────────────────────────────────────────────────────────────────

def test_record_metric_ok(test_db):
    out = perf.record_performance_metric(metric_type="response_time_ms", value=120,
                                         user=_user(test_db), db=test_db)
    assert out["value"] == 120


def test_record_metric_invalid_type(test_db):
    with pytest.raises(HTTPException) as ei:
        perf.record_performance_metric(metric_type="bad", value=1,
                                       user=_user(test_db), db=test_db)
    assert ei.value.status_code == 400


# ── baselines ────────────────────────────────────────────────────────────────

def test_list_baselines(test_db):
    user = _user(test_db)
    create_baseline(test_db, MetricType.RESPONSE_TIME, [float(i) for i in range(1, 101)])
    out = perf.list_baselines(metric_type="response_time_ms", user=user, db=test_db)
    assert out["total"] >= 1


def test_list_baselines_invalid_type(test_db):
    with pytest.raises(HTTPException) as ei:
        perf.list_baselines(metric_type="bad", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 400


def test_create_baseline_insufficient(test_db):
    user = _user(test_db)
    _seed_metrics(test_db, n=3)
    with pytest.raises(HTTPException) as ei:
        perf.create_performance_baseline(metric_type="response_time_ms", hours=1, user=user, db=test_db)
    assert ei.value.status_code == 400


def test_create_baseline_ok(test_db):
    user = _user(test_db)
    _seed_metrics(test_db, n=12)
    out = perf.create_performance_baseline(metric_type="response_time_ms", hours=1, user=user, db=test_db)
    assert out["sample_count"] == 12


def test_create_baseline_invalid_type(test_db):
    with pytest.raises(HTTPException) as ei:
        perf.create_performance_baseline(metric_type="bad", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 400


# ── regressions ──────────────────────────────────────────────────────────────

def test_check_for_regressions(test_db):
    user = _user(test_db)
    _seed_metrics(test_db, n=12, value=115)
    create_baseline(test_db, MetricType.RESPONSE_TIME, [100.0] * 100)
    out = perf.check_for_regressions(hours=1, threshold_percent=10.0, user=user, db=test_db)
    assert "total_metrics_checked" in out
    assert "alerts" in out


def test_detect_endpoint_regression_no_baseline(test_db):
    with pytest.raises(HTTPException) as ei:
        perf.detect_endpoint_regression(metric_type="response_time_ms", hours=1,
                                        user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


def test_detect_endpoint_regression_invalid_type(test_db):
    with pytest.raises(HTTPException) as ei:
        perf.detect_endpoint_regression(metric_type="bad", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 400


def test_detect_endpoint_regression_ok(test_db):
    user = _user(test_db)
    create_baseline(test_db, MetricType.RESPONSE_TIME, [100.0] * 100)
    _seed_metrics(test_db, n=6, value=130)
    out = perf.detect_endpoint_regression(metric_type="response_time_ms", hours=1, user=user, db=test_db)
    assert out["is_regression"] is True
    assert out["severity"] in ("high", "critical", "medium")


def test_detect_endpoint_regression_insufficient(test_db):
    user = _user(test_db)
    create_baseline(test_db, MetricType.RESPONSE_TIME, [100.0] * 100)
    _seed_metrics(test_db, n=2, value=130)
    with pytest.raises(HTTPException) as ei:
        perf.detect_endpoint_regression(metric_type="response_time_ms", hours=1, user=user, db=test_db)
    assert ei.value.status_code == 400


# ── dashboard ────────────────────────────────────────────────────────────────

def test_performance_dashboard(test_db):
    user = _user(test_db)
    _seed_metrics(test_db, n=12, value=110)
    create_baseline(test_db, MetricType.RESPONSE_TIME, [100.0] * 100)
    out = perf.get_performance_dashboard(hours=24, user=user, db=test_db)
    assert "metrics" in out
    assert out["metrics"]["response_time_ms"]["count"] == 12
