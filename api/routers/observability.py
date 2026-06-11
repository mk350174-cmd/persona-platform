"""Observability & Monitoring — Endpoints for metrics, traces, and logs."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from api.db import get_db, User
from api.auth import get_current_user
from api.observability import (
    get_metrics_collector,
    get_request_metrics,
    get_structured_logger,
    Span,
)

router = APIRouter(prefix="/observability", tags=["observability"])
logger = get_structured_logger("observability_router")


# ── Metrics Endpoints ─────────────────────────────────────────────────────────

@router.get("/metrics")
def get_metrics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current metrics in Prometheus format."""
    collector = get_metrics_collector()
    metrics = collector.get_metrics()

    logger.info(
        "Metrics retrieved",
        user_id=user.id,
        metric_count=len(metrics),
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "total_metrics": len(metrics),
    }


@router.post("/metrics/record")
def record_metric(
    name: str,
    metric_type: str,
    value: float,
    labels: Optional[Dict[str, str]] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a metric."""
    collector = get_metrics_collector()

    if metric_type not in ["counter", "gauge", "histogram", "summary"]:
        raise HTTPException(status_code=400, detail=f"Invalid metric_type: {metric_type}")

    try:
        if metric_type == "counter":
            collector.record_counter(name, value, labels)
        elif metric_type == "gauge":
            collector.record_gauge(name, value, labels)
        elif metric_type == "histogram":
            collector.record_histogram(name, value, labels)
        elif metric_type == "summary":
            # Treat summary like histogram for now
            collector.record_histogram(name, value, labels)
    except Exception as e:
        logger.error(
            "Failed to record metric",
            metric_name=name,
            metric_type=metric_type,
            error=str(e),
            user_id=user.id,
        )
        raise HTTPException(status_code=500, detail=f"Failed to record metric: {str(e)}")

    logger.info(
        "Metric recorded",
        metric_name=name,
        metric_type=metric_type,
        value=value,
        user_id=user.id,
    )

    return {
        "status": "recorded",
        "name": name,
        "type": metric_type,
        "value": value,
    }


@router.get("/metrics/summary")
def get_metrics_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get high-level metrics summary."""
    req_metrics = get_request_metrics()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_requests": req_metrics.total_requests,
        "successful_requests": req_metrics.successful_requests,
        "failed_requests": req_metrics.failed_requests,
        "average_duration_ms": round(req_metrics.average_duration_ms, 2),
        "success_rate": round(req_metrics.success_rate * 100, 2),
    }


# ── Request Tracing Endpoints ─────────────────────────────────────────────────

@router.post("/traces/record")
def record_trace(
    trace_id: str,
    span_id: str,
    operation: str,
    duration_ms: float,
    status: str = "OK",
    tags: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a distributed trace span."""
    if status not in ["OK", "ERROR", "CANCELLED"]:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    span = Span(
        trace_id=trace_id,
        span_id=span_id,
        operation=operation,
        tags=tags or {},
    )
    span.end_time = span.start_time + (duration_ms / 1000.0)
    span.duration_ms = duration_ms
    span.status = status
    span.error = error

    # In production, send to Jaeger
    logger.info(
        "Span recorded",
        trace_id=trace_id,
        span_id=span_id,
        operation=operation,
        duration_ms=duration_ms,
        status=status,
        user_id=user.id,
    )

    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "operation": operation,
        "duration_ms": duration_ms,
        "status": status,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/traces/{trace_id}")
def get_trace(
    trace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get trace details by ID (in production, would fetch from Jaeger)."""
    # In production, query Jaeger for this trace
    logger.info(
        "Trace retrieved",
        trace_id=trace_id,
        user_id=user.id,
    )

    return {
        "trace_id": trace_id,
        "status": "trace_retrieval_not_implemented",
        "message": "In production, traces are stored in Jaeger. This endpoint would query the Jaeger backend.",
        "note": "See OBSERVABILITY.md for Jaeger integration setup.",
    }


# ── Health Check Endpoints ────────────────────────────────────────────────────

@router.get("/health/deep")
def deep_health_check(
    db: Session = Depends(get_db),
):
    """Deep health check including database connectivity."""
    checks = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "healthy",
        "checks": {},
    }

    # Database connectivity check
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        checks["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        checks["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        checks["status"] = "degraded"

    # Metrics collector check
    try:
        collector = get_metrics_collector()
        metric_count = len(collector.metrics)
        checks["checks"]["metrics"] = {"status": "healthy", "metric_count": metric_count}
    except Exception as e:
        checks["checks"]["metrics"] = {"status": "unhealthy", "error": str(e)}
        checks["status"] = "degraded"

    # Request metrics check
    try:
        req_metrics = get_request_metrics()
        checks["checks"]["request_metrics"] = {
            "status": "healthy",
            "total_requests": req_metrics.total_requests,
        }
    except Exception as e:
        checks["checks"]["request_metrics"] = {"status": "unhealthy", "error": str(e)}
        checks["status"] = "degraded"

    return checks


@router.get("/health/liveness")
def liveness_check():
    """Liveness check — pod is running."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/readiness")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness check — pod is ready to receive traffic."""
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {str(e)}",
        )


# ── Logging Endpoints ─────────────────────────────────────────────────────────

@router.post("/logs/collect")
def collect_logs(
    level: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_user),
):
    """Collect structured logs from clients."""
    if level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        raise HTTPException(status_code=400, detail=f"Invalid log level: {level}")

    log_data = {
        "level": level,
        "message": message,
        **(context or {}),
        "client_user_id": user.id,
    }

    if level == "DEBUG":
        logger.debug(message, **log_data)
    elif level == "INFO":
        logger.info(message, **log_data)
    elif level == "WARNING":
        logger.warning(message, **log_data)
    elif level == "ERROR":
        logger.error(message, **log_data)

    return {
        "status": "logged",
        "level": level,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Prometheus Integration ────────────────────────────────────────────────────

@router.get("/prometheus/metrics")
def prometheus_metrics(
    user: User = Depends(get_current_user),
):
    """Export metrics in Prometheus text format (for scraping)."""
    collector = get_metrics_collector()
    req_metrics = get_request_metrics()

    # Generate Prometheus format
    lines = []

    # Standard HTTP metrics
    lines.append("# HELP http_requests_total Total HTTP requests")
    lines.append("# TYPE http_requests_total counter")
    lines.append(f"http_requests_total {req_metrics.total_requests}")

    lines.append("# HELP http_requests_success Successful HTTP requests")
    lines.append("# TYPE http_requests_success counter")
    lines.append(f"http_requests_success {req_metrics.successful_requests}")

    lines.append("# HELP http_requests_failed Failed HTTP requests")
    lines.append("# TYPE http_requests_failed counter")
    lines.append(f"http_requests_failed {req_metrics.failed_requests}")

    lines.append("# HELP http_request_duration_ms HTTP request duration in milliseconds")
    lines.append("# TYPE http_request_duration_ms gauge")
    lines.append(f"http_request_duration_ms {req_metrics.average_duration_ms}")

    lines.append("# HELP http_requests_success_rate HTTP success rate")
    lines.append("# TYPE http_requests_success_rate gauge")
    lines.append(f"http_requests_success_rate {req_metrics.success_rate}")

    # Custom metrics from collector
    lines.append("# HELP custom_metrics Custom application metrics")
    lines.append("# TYPE custom_metrics untyped")
    lines.extend(collector.get_metrics())

    return "\n".join(lines) + "\n"
