"""Performance Monitoring API — Metrics and regression detection."""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from api.db import get_db, User, PerformanceMetric
from api.auth import get_current_user
from api.performance_metrics import (
    MetricType,
    record_metric,
    get_recent_metrics,
    create_baseline,
    get_latest_baseline,
    detect_regression,
    check_all_metrics_for_regression,
    should_alert_on_regression,
    format_regression_alert,
)

router = APIRouter(prefix="/performance", tags=["performance-monitoring"])


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/metrics")
def list_metrics(
    metric_type: Optional[str] = None,
    endpoint: Optional[str] = None,
    hours: int = Query(1, ge=1, le=168),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent performance metrics."""
    if not metric_type:
        raise HTTPException(status_code=400, detail="metric_type parameter required")

    try:
        mtype = MetricType(metric_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric_type. Must be one of: {', '.join(m.value for m in MetricType)}",
        )

    metrics = get_recent_metrics(db, mtype, hours=hours, endpoint=endpoint)

    return {
        "metric_type": metric_type,
        "endpoint": endpoint,
        "hours": hours,
        "count": len(metrics),
        "metrics": [
            {
                "value": m.value,
                "recorded_at": m.recorded_at,
                "tags": m.tags,
            }
            for m in metrics
        ],
    }


@router.post("/metrics/record")
def record_performance_metric(
    metric_type: str,
    value: float,
    endpoint: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a performance metric (for integration with monitoring tools)."""
    try:
        mtype = MetricType(metric_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric_type. Must be one of: {', '.join(m.value for m in MetricType)}",
        )

    record_metric(db, mtype, value, endpoint=endpoint)

    return {
        "message": "Metric recorded successfully",
        "metric_type": metric_type,
        "value": value,
        "endpoint": endpoint,
    }


@router.get("/baselines")
def list_baselines(
    metric_type: Optional[str] = None,
    endpoint: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all performance baselines."""
    from api.db import PerformanceBaseline as BaselineModel

    query = db.query(BaselineModel)

    if metric_type:
        try:
            mtype = MetricType(metric_type)
            query = query.filter(BaselineModel.metric_type == mtype.value)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid metric_type")

    if endpoint:
        query = query.filter(BaselineModel.endpoint == endpoint)

    baselines = query.order_by(BaselineModel.created_at.desc()).all()

    return {
        "baselines": [
            {
                "id": b.id,
                "metric_type": b.metric_type,
                "endpoint": b.endpoint,
                "p50": b.p50,
                "p95": b.p95,
                "p99": b.p99,
                "mean": b.mean,
                "stddev": b.stddev,
                "min": b.min_val,
                "max": b.max_val,
                "sample_count": b.sample_count,
                "created_at": b.created_at,
            }
            for b in baselines
        ],
        "total": len(baselines),
    }


@router.post("/baselines/create")
def create_performance_baseline(
    metric_type: str,
    hours: int = Query(1, ge=1, le=168),
    endpoint: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new performance baseline from recent metrics."""
    try:
        mtype = MetricType(metric_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid metric_type")

    metrics = get_recent_metrics(db, mtype, hours=hours, endpoint=endpoint)

    if not metrics or len(metrics) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 10 samples. Found {len(metrics)}",
        )

    values = [m.value for m in metrics]
    baseline = create_baseline(db, mtype, values, endpoint=endpoint)

    return {
        "message": "Baseline created successfully",
        "metric_type": metric_type,
        "endpoint": endpoint,
        "sample_count": len(values),
        "p50": baseline.p50,
        "p95": baseline.p95,
        "p99": baseline.p99,
        "mean": baseline.mean,
        "stddev": baseline.stddev,
        "created_at": baseline.created_at,
    }


@router.get("/regressions/check")
def check_for_regressions(
    hours: int = Query(1, ge=1, le=24),
    threshold_percent: float = Query(10.0, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check for performance regressions."""
    results = check_all_metrics_for_regression(db, hours_window=hours, regression_threshold_percent=threshold_percent)

    alerts = []
    for result in results:
        if should_alert_on_regression(result):
            alert = format_regression_alert(result)
            alerts.append(alert)

    return {
        "window_hours": hours,
        "threshold_percent": threshold_percent,
        "total_metrics_checked": len(results),
        "regressions_detected": len([r for r in results if r.is_regression]),
        "alerts": alerts,
        "all_results": [
            {
                "metric_type": r.metric_type.value,
                "endpoint": r.endpoint,
                "is_regression": r.is_regression,
                "severity": r.severity.value,
                "percent_change": r.percent_change,
                "baseline_p95": r.baseline.p95,
                "current_p95": r.current_value,
                "confidence": r.confidence,
                "explanation": r.explanation,
            }
            for r in results
        ],
    }


@router.post("/regressions/detect")
def detect_endpoint_regression(
    metric_type: str,
    hours: int = Query(1, ge=1, le=24),
    endpoint: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detect regression for specific metric/endpoint."""
    try:
        mtype = MetricType(metric_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid metric_type")

    # Get baseline
    baseline = get_latest_baseline(db, mtype, endpoint=endpoint)
    if not baseline:
        raise HTTPException(status_code=404, detail="No baseline found for this metric")

    # Get recent metrics
    recent_metrics = get_recent_metrics(db, mtype, hours=hours, endpoint=endpoint)
    if not recent_metrics or len(recent_metrics) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 5 recent metrics. Found {len(recent_metrics)}",
        )

    values = [m.value for m in recent_metrics]
    result = detect_regression(baseline, values)

    alert = None
    if should_alert_on_regression(result):
        alert = format_regression_alert(result)

    return {
        "metric_type": metric_type,
        "endpoint": endpoint,
        "is_regression": result.is_regression,
        "severity": result.severity.value,
        "percent_change": result.percent_change,
        "baseline": {
            "p50": baseline.p50,
            "p95": baseline.p95,
            "p99": baseline.p99,
            "mean": baseline.mean,
            "stddev": baseline.stddev,
            "sample_count": baseline.sample_count,
            "created_at": baseline.created_at,
        },
        "current": {
            "p95": result.current_value,
            "samples": len(values),
        },
        "explanation": result.explanation,
        "confidence": result.confidence,
        "alert": alert,
    }


@router.get("/dashboard/summary")
def get_performance_dashboard(
    hours: int = Query(24, ge=1, le=168),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get performance dashboard summary."""
    metrics_by_type = {}

    for metric_type in MetricType:
        metrics = get_recent_metrics(db, metric_type, hours=hours)
        baseline = get_latest_baseline(db, metric_type)

        if metrics:
            values = [m.value for m in metrics]
            import statistics

            metrics_by_type[metric_type.value] = {
                "count": len(values),
                "current_p95": sorted(values)[int(0.95 * len(values) - 1)] if values else 0,
                "mean": statistics.mean(values),
                "baseline_p95": baseline.p95 if baseline else None,
                "baseline_exists": baseline is not None,
            }

    return {
        "window_hours": hours,
        "summary_time": datetime.now(timezone.utc),
        "metrics": metrics_by_type,
    }
