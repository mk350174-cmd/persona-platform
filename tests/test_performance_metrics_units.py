"""
Unit tests for api/performance_metrics.py — baseline stats + regression detection.

Pure stats/logic need no DB; record/query/baseline persistence use `test_db`.
"""

import pytest

from api.performance_metrics import (
    MetricType,
    RegressionSeverity,
    PerformanceBaseline,
    record_metric,
    get_recent_metrics,
    calculate_baseline,
    create_baseline,
    get_latest_baseline,
    detect_regression,
    _generate_regression_explanation,
    check_all_metrics_for_regression,
    should_alert_on_regression,
    format_regression_alert,
    _get_recommended_action,
)
from datetime import datetime, timezone


# ── calculate_baseline ───────────────────────────────────────────────────────

def test_calculate_baseline_empty():
    assert calculate_baseline([]) == (0, 0, 0, 0, 0, 0, 0)


def test_calculate_baseline_basic_stats():
    vals = [float(i) for i in range(1, 101)]   # 1..100
    p50, p95, p99, mean, stddev, mn, mx = calculate_baseline(vals)
    assert mn == 1 and mx == 100
    assert mean == pytest.approx(50.5)
    assert p50 == pytest.approx(50.5)
    assert stddev > 0


def test_calculate_baseline_single_value_zero_stddev():
    p50, p95, p99, mean, stddev, mn, mx = calculate_baseline([42.0])
    assert stddev == 0 and mean == 42.0 and mn == mx == 42.0


# ── detect_regression ────────────────────────────────────────────────────────

def _baseline(p95=100.0):
    return PerformanceBaseline(
        metric_type=MetricType.RESPONSE_TIME, endpoint="/chat",
        p50=80.0, p95=p95, p99=120.0, mean=85.0, stddev=10.0,
        min=50.0, max=150.0, sample_count=100, created_at=datetime.now(timezone.utc),
    )


def test_detect_regression_no_current_metrics():
    r = detect_regression(_baseline(), [])
    assert r.is_regression is False
    assert r.explanation == "Insufficient data for comparison"


def test_detect_regression_stable():
    # current p95 ≈ baseline → no regression
    r = detect_regression(_baseline(100.0), [100.0] * 50)
    assert r.is_regression is False
    assert r.severity == RegressionSeverity.LOW


def test_detect_regression_medium():
    # +15% over baseline p95 → MEDIUM
    r = detect_regression(_baseline(100.0), [115.0] * 50)
    assert r.is_regression is True
    assert r.severity == RegressionSeverity.MEDIUM


def test_detect_regression_high():
    r = detect_regression(_baseline(100.0), [130.0] * 50)
    assert r.severity == RegressionSeverity.HIGH
    assert r.is_regression is True


def test_detect_regression_critical():
    r = detect_regression(_baseline(100.0), [200.0] * 50)
    assert r.severity == RegressionSeverity.CRITICAL
    assert "CRITICAL" in r.explanation


def test_detect_regression_zero_baseline_p95():
    r = detect_regression(_baseline(0.0), [50.0] * 20)
    assert r.percent_change == 0


def test_confidence_scales_with_sample_size():
    small = detect_regression(_baseline(100.0), [115.0] * 10)
    large = detect_regression(_baseline(100.0), [115.0] * 100)
    assert small.confidence < large.confidence
    assert large.confidence == pytest.approx(1.0)


# ── explanation / alerting ───────────────────────────────────────────────────

def test_generate_explanation_direction():
    b = _baseline(100.0)
    up = _generate_regression_explanation(b, 130.0, 30.0, RegressionSeverity.HIGH)
    assert "increased" in up and "HIGH" in up
    down = _generate_regression_explanation(b, 70.0, -30.0, RegressionSeverity.LOW)
    assert "decreased" in down


def test_should_alert_on_regression_rules():
    crit = detect_regression(_baseline(100.0), [200.0] * 100)
    assert should_alert_on_regression(crit) is True

    stable = detect_regression(_baseline(100.0), [100.0] * 100)
    assert should_alert_on_regression(stable) is False

    # MEDIUM needs confidence > 0.7
    med_lowconf = detect_regression(_baseline(100.0), [115.0] * 10)   # conf 0.1
    assert should_alert_on_regression(med_lowconf) is False
    med_highconf = detect_regression(_baseline(100.0), [115.0] * 100)  # conf 1.0
    assert should_alert_on_regression(med_highconf) is True


def test_format_regression_alert_shape():
    r = detect_regression(_baseline(100.0), [200.0] * 100)
    alert = format_regression_alert(r)
    assert alert["severity"] == "CRITICAL"
    assert alert["metric"] == "response_time_ms"
    assert alert["endpoint"] == "/chat"
    assert alert["change_percent"].endswith("%")
    assert "action" in alert


def test_recommended_actions_per_severity():
    crit = detect_regression(_baseline(100.0), [200.0] * 100)
    assert "URGENT" in _get_recommended_action(crit)
    high = detect_regression(_baseline(100.0), [130.0] * 100)
    assert "Investigate" in _get_recommended_action(high)
    med = detect_regression(_baseline(100.0), [115.0] * 100)
    assert "Monitor" in _get_recommended_action(med)
    stable = detect_regression(_baseline(100.0), [100.0] * 100)
    assert "observe" in _get_recommended_action(stable).lower()


# ── DB-backed: record / query / baseline ─────────────────────────────────────

def test_record_and_get_recent_metrics(test_db):
    for v in (100, 110, 120):
        record_metric(test_db, MetricType.RESPONSE_TIME, v, endpoint="/chat")
    rows = get_recent_metrics(test_db, MetricType.RESPONSE_TIME, hours=1, endpoint="/chat")
    assert len(rows) == 3
    assert [r.value for r in rows] == [100, 110, 120]


def test_get_recent_metrics_endpoint_filter(test_db):
    record_metric(test_db, MetricType.RESPONSE_TIME, 100, endpoint="/a")
    record_metric(test_db, MetricType.RESPONSE_TIME, 200, endpoint="/b")
    only_a = get_recent_metrics(test_db, MetricType.RESPONSE_TIME, endpoint="/a")
    assert len(only_a) == 1 and only_a[0].endpoint == "/a"


def test_create_and_get_latest_baseline(test_db):
    created = create_baseline(test_db, MetricType.RESPONSE_TIME,
                              [float(i) for i in range(1, 101)], endpoint="/chat")
    assert isinstance(created, PerformanceBaseline)
    latest = get_latest_baseline(test_db, MetricType.RESPONSE_TIME, endpoint="/chat")
    assert latest is not None
    assert latest.metric_type == MetricType.RESPONSE_TIME
    assert latest.sample_count == 100


def test_get_latest_baseline_none_when_absent(test_db):
    assert get_latest_baseline(test_db, MetricType.CPU_USAGE) is None


def test_baseline_margin_of_error_property():
    b = _baseline()
    assert b.margin_of_error > 0
    empty = PerformanceBaseline(
        metric_type=MetricType.RESPONSE_TIME, endpoint=None, p50=0, p95=0, p99=0,
        mean=0, stddev=0, min=0, max=0, sample_count=0, created_at=datetime.now(timezone.utc),
    )
    assert empty.margin_of_error == 0


def test_check_all_metrics_for_regression(test_db):
    # need >= 10 recent metrics + a baseline for the type to be evaluated
    for v in [115] * 12:
        record_metric(test_db, MetricType.RESPONSE_TIME, v, endpoint=None)
    create_baseline(test_db, MetricType.RESPONSE_TIME, [100.0] * 100)
    results = check_all_metrics_for_regression(test_db, hours_window=1)
    assert any(r.metric_type == MetricType.RESPONSE_TIME for r in results)


def test_check_all_metrics_skips_when_too_few(test_db):
    record_metric(test_db, MetricType.MEMORY_USAGE, 100)
    # only 1 sample (< 10) → skipped, no baseline anyway
    assert check_all_metrics_for_regression(test_db) == []
