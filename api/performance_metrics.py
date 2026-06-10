"""
Performance Metrics & Regression Detection

Tracks baseline performance metrics and detects regressions:
- Response latency (p50, p95, p99)
- Throughput (requests/sec)
- Error rate (5xx, 4xx)
- Database query time
- Endpoint-specific metrics
"""

import statistics
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from sqlalchemy.orm import Session


class MetricType(Enum):
    """Types of metrics tracked."""
    RESPONSE_TIME = "response_time_ms"
    ERROR_RATE = "error_rate_percent"
    THROUGHPUT = "requests_per_sec"
    DB_QUERY_TIME = "db_query_ms"
    MEMORY_USAGE = "memory_mb"
    CPU_USAGE = "cpu_percent"


class RegressionSeverity(Enum):
    """Regression severity levels."""
    CRITICAL = "critical"  # > 50% degradation
    HIGH = "high"          # > 25% degradation
    MEDIUM = "medium"      # > 10% degradation
    LOW = "low"            # > 5% degradation


@dataclass
class MetricDatapoint:
    """Single metric measurement."""
    value: float
    timestamp: datetime
    endpoint: Optional[str] = None
    tags: dict = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class PerformanceBaseline:
    """Baseline metrics for comparison."""
    metric_type: MetricType
    endpoint: Optional[str]
    p50: float
    p95: float
    p99: float
    mean: float
    stddev: float
    min: float
    max: float
    sample_count: int
    created_at: datetime

    @property
    def margin_of_error(self) -> float:
        """95% confidence interval margin."""
        return 1.96 * self.stddev / (self.sample_count ** 0.5) if self.sample_count > 0 else 0


@dataclass
class RegressionResult:
    """Result of regression detection."""
    metric_type: MetricType
    endpoint: Optional[str]
    baseline: PerformanceBaseline
    current_value: float
    previous_value: float
    percent_change: float
    severity: RegressionSeverity
    is_regression: bool
    explanation: str
    confidence: float  # 0.0-1.0


# ── Metrics Collection ────────────────────────────────────────────────────────


def record_metric(
    db: Session,
    metric_type: MetricType,
    value: float,
    endpoint: Optional[str] = None,
    tags: Optional[dict] = None,
) -> None:
    """Record a performance metric."""
    from api.db import PerformanceMetric
    import secrets

    metric = PerformanceMetric(
        id=f"metric_{secrets.token_hex(8)}",
        metric_type=metric_type.value,
        value=value,
        endpoint=endpoint,
        tags=tags or {},
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(metric)
    db.commit()


def get_recent_metrics(
    db: Session,
    metric_type: MetricType,
    hours: int = 1,
    endpoint: Optional[str] = None,
) -> list["PerformanceMetric"]:
    """Get recent metrics for analysis."""
    from api.db import PerformanceMetric

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = db.query(PerformanceMetric).filter(
        PerformanceMetric.metric_type == metric_type.value,
        PerformanceMetric.recorded_at >= cutoff,
    )

    if endpoint:
        query = query.filter(PerformanceMetric.endpoint == endpoint)

    return query.order_by(PerformanceMetric.recorded_at).all()


# ── Baseline Calculation ──────────────────────────────────────────────────────


def calculate_baseline(
    metrics: list[float],
) -> tuple[float, float, float, float, float, float, float]:
    """Calculate baseline statistics from metrics.

    Returns: (p50, p95, p99, mean, stddev, min, max)
    """
    if not metrics:
        return 0, 0, 0, 0, 0, 0, 0

    sorted_metrics = sorted(metrics)
    n = len(sorted_metrics)

    p50 = statistics.median(sorted_metrics)
    p95 = sorted_metrics[int(0.95 * n - 1)] if n > 0 else 0
    p99 = sorted_metrics[int(0.99 * n - 1)] if n > 0 else 0
    mean = statistics.mean(sorted_metrics)
    stddev = statistics.stdev(sorted_metrics) if n > 1 else 0
    min_val = min(sorted_metrics)
    max_val = max(sorted_metrics)

    return p50, p95, p99, mean, stddev, min_val, max_val


def create_baseline(
    db: Session,
    metric_type: MetricType,
    metrics: list[float],
    endpoint: Optional[str] = None,
) -> "PerformanceBaseline":
    """Create a performance baseline from metrics."""
    from api.db import PerformanceBaseline as BaselineModel
    import secrets

    p50, p95, p99, mean, stddev, min_val, max_val = calculate_baseline(metrics)

    baseline = BaselineModel(
        id=f"baseline_{secrets.token_hex(8)}",
        metric_type=metric_type.value,
        endpoint=endpoint,
        p50=p50,
        p95=p95,
        p99=p99,
        mean=mean,
        stddev=stddev,
        min_val=min_val,
        max_val=max_val,
        sample_count=len(metrics),
        created_at=datetime.now(timezone.utc),
    )
    db.add(baseline)
    db.commit()
    db.refresh(baseline)

    return _model_to_dataclass(baseline)


def get_latest_baseline(
    db: Session,
    metric_type: MetricType,
    endpoint: Optional[str] = None,
) -> Optional[PerformanceBaseline]:
    """Get most recent baseline for metric type."""
    from api.db import PerformanceBaseline as BaselineModel

    query = db.query(BaselineModel).filter(
        BaselineModel.metric_type == metric_type.value
    )

    if endpoint:
        query = query.filter(BaselineModel.endpoint == endpoint)

    baseline = query.order_by(BaselineModel.created_at.desc()).first()
    return _model_to_dataclass(baseline) if baseline else None


# ── Regression Detection ──────────────────────────────────────────────────────


def _model_to_dataclass(baseline) -> PerformanceBaseline:
    """Convert database model to dataclass."""
    return PerformanceBaseline(
        metric_type=MetricType(baseline.metric_type),
        endpoint=baseline.endpoint,
        p50=baseline.p50,
        p95=baseline.p95,
        p99=baseline.p99,
        mean=baseline.mean,
        stddev=baseline.stddev,
        min=baseline.min_val,
        max=baseline.max_val,
        sample_count=baseline.sample_count,
        created_at=baseline.created_at,
    )


def detect_regression(
    baseline: PerformanceBaseline,
    current_metrics: list[float],
    regression_threshold_percent: float = 10.0,
) -> RegressionResult:
    """Detect performance regression by comparing current metrics to baseline.

    Returns RegressionResult with severity and explanation.
    """
    if not current_metrics or not baseline:
        return RegressionResult(
            metric_type=baseline.metric_type,
            endpoint=baseline.endpoint,
            baseline=baseline,
            current_value=0,
            previous_value=baseline.mean,
            percent_change=0,
            severity=RegressionSeverity.LOW,
            is_regression=False,
            explanation="Insufficient data for comparison",
            confidence=0,
        )

    current_p95 = sorted(current_metrics)[int(0.95 * len(current_metrics) - 1)]
    percent_change = ((current_p95 - baseline.p95) / baseline.p95 * 100) if baseline.p95 > 0 else 0

    # Determine severity
    if percent_change < regression_threshold_percent:
        severity = RegressionSeverity.LOW
        is_regression = False
    elif percent_change < 10:
        severity = RegressionSeverity.LOW
        is_regression = False
    elif percent_change < 25:
        severity = RegressionSeverity.MEDIUM
        is_regression = True
    elif percent_change < 50:
        severity = RegressionSeverity.HIGH
        is_regression = True
    else:
        severity = RegressionSeverity.CRITICAL
        is_regression = True

    # Calculate confidence (based on sample size and variability)
    confidence = min(1.0, len(current_metrics) / 100)

    explanation = _generate_regression_explanation(
        baseline, current_p95, percent_change, severity
    )

    return RegressionResult(
        metric_type=baseline.metric_type,
        endpoint=baseline.endpoint,
        baseline=baseline,
        current_value=current_p95,
        previous_value=baseline.p95,
        percent_change=round(percent_change, 1),
        severity=severity,
        is_regression=is_regression,
        explanation=explanation,
        confidence=confidence,
    )


def _generate_regression_explanation(
    baseline: PerformanceBaseline,
    current_value: float,
    percent_change: float,
    severity: RegressionSeverity,
) -> str:
    """Generate human-readable explanation of regression."""
    metric_name = baseline.metric_type.value
    direction = "increased" if percent_change > 0 else "decreased"

    explanation = (
        f"{metric_name} {direction} by {abs(percent_change):.1f}% "
        f"(baseline: {baseline.p95:.2f}, current: {current_value:.2f})"
    )

    if severity == RegressionSeverity.CRITICAL:
        explanation += " — CRITICAL: >50% degradation detected"
    elif severity == RegressionSeverity.HIGH:
        explanation += " — HIGH: 25-50% degradation"
    elif severity == RegressionSeverity.MEDIUM:
        explanation += " — MEDIUM: 10-25% degradation"

    return explanation


def check_all_metrics_for_regression(
    db: Session,
    hours_window: int = 1,
    regression_threshold_percent: float = 10.0,
) -> list[RegressionResult]:
    """Check all active metrics for regressions."""
    from api.db import PerformanceMetric

    results = []

    # Get unique metric types
    metric_types = db.query(PerformanceMetric.metric_type).distinct().all()

    for (metric_type_str,) in metric_types:
        metric_type = MetricType(metric_type_str)

        # Get recent metrics
        recent_metrics = get_recent_metrics(db, metric_type, hours=hours_window)
        if not recent_metrics or len(recent_metrics) < 10:
            continue

        values = [m.value for m in recent_metrics]

        # Get baseline
        baseline = get_latest_baseline(db, metric_type)
        if not baseline:
            continue

        # Detect regression
        result = detect_regression(baseline, values, regression_threshold_percent)
        results.append(result)

    return results


# ── Alerting ──────────────────────────────────────────────────────────────────


def should_alert_on_regression(result: RegressionResult) -> bool:
    """Determine if regression warrants an alert."""
    if not result.is_regression:
        return False

    if result.severity in [RegressionSeverity.CRITICAL, RegressionSeverity.HIGH]:
        return True

    if result.severity == RegressionSeverity.MEDIUM and result.confidence > 0.7:
        return True

    return False


def format_regression_alert(result: RegressionResult) -> dict:
    """Format regression result for alerting (Slack, email, etc.)."""
    severity_emoji = {
        RegressionSeverity.CRITICAL: "🚨",
        RegressionSeverity.HIGH: "⚠️",
        RegressionSeverity.MEDIUM: "⚡",
        RegressionSeverity.LOW: "ℹ️",
    }

    return {
        "title": f"{severity_emoji[result.severity]} Performance Regression Detected",
        "metric": result.metric_type.value,
        "endpoint": result.endpoint or "global",
        "severity": result.severity.value.upper(),
        "change_percent": f"{result.percent_change:+.1f}%",
        "baseline_p95": f"{result.baseline.p95:.2f}ms",
        "current_p95": f"{result.current_value:.2f}ms",
        "explanation": result.explanation,
        "confidence": f"{result.confidence * 100:.0f}%",
        "action": _get_recommended_action(result),
    }


def _get_recommended_action(result: RegressionResult) -> str:
    """Get recommended action based on regression severity."""
    if result.severity == RegressionSeverity.CRITICAL:
        return "URGENT: Consider rollback or disabling recent changes"
    elif result.severity == RegressionSeverity.HIGH:
        return "Investigate recent code changes and deployments"
    elif result.severity == RegressionSeverity.MEDIUM:
        return "Monitor closely, investigate if trend continues"
    else:
        return "Log and observe, may be within normal variation"
