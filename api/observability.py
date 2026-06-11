"""
Observability & Monitoring — Distributed tracing, metrics, structured logging

Integrations:
- Jaeger/OpenTelemetry: Distributed tracing
- Prometheus: Metrics aggregation
- Structured logging: JSON logs with context
- APM instrumentation: Application performance tracking
"""

import time
import logging
import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

# Configure structured logging
class StructuredLogger:
    """JSON-formatted structured logger with trace context."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _format_log(self, level: str, message: str, **context) -> str:
        """Format log entry as JSON with context."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            **context,
        }
        return json.dumps(entry)

    def info(self, message: str, **context):
        """Log info level with context."""
        self.logger.info(self._format_log("INFO", message, **context))

    def warning(self, message: str, **context):
        """Log warning level with context."""
        self.logger.warning(self._format_log("WARNING", message, **context))

    def error(self, message: str, **context):
        """Log error level with context."""
        self.logger.error(self._format_log("ERROR", message, **context))

    def debug(self, message: str, **context):
        """Log debug level with context."""
        self.logger.debug(self._format_log("DEBUG", message, **context))


# ── Trace Context ─────────────────────────────────────────────────────────────

@dataclass
class TraceContext:
    """Distributed trace context (similar to W3C Trace Context)."""
    trace_id: str  # Unique trace identifier
    span_id: str  # Current span identifier
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = None  # Cross-cutting context

    def __post_init__(self):
        if self.baggage is None:
            self.baggage = {}

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers for propagation."""
        return {
            "traceparent": f"00-{self.trace_id}-{self.span_id}-01",
            "baggage": ",".join(f"{k}={v}" for k, v in self.baggage.items()),
        }

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> "TraceContext":
        """Parse from HTTP headers."""
        import secrets
        import uuid

        traceparent = headers.get("traceparent", "")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 4:
                return cls(
                    trace_id=parts[1],
                    span_id=parts[2],
                    parent_span_id=parts[2],
                )

        return cls(
            trace_id=uuid.uuid4().hex,
            span_id=secrets.token_hex(8),
        )


# ── Span Recording ────────────────────────────────────────────────────────────

@dataclass
class Span:
    """Recorded span for distributed tracing."""
    trace_id: str
    span_id: str
    operation: str
    service: str = "persona-platform"
    start_time: float = None
    end_time: float = None
    duration_ms: float = None
    status: str = "OK"  # OK, ERROR, CANCELLED
    tags: Dict[str, Any] = None
    logs: list = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.logs is None:
            self.logs = []
        if self.start_time is None:
            self.start_time = time.time()

    def finish(self, status: str = "OK", error: Optional[str] = None):
        """Mark span as finished."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error

    def add_tag(self, key: str, value: Any):
        """Add tag to span."""
        self.tags[key] = value

    def add_log(self, message: str, **fields):
        """Add log entry to span."""
        self.logs.append({
            "timestamp": time.time(),
            "message": message,
            **fields,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for serialization."""
        return {
            "traceID": self.trace_id,
            "spanID": self.span_id,
            "operationName": self.operation,
            "startTime": int(self.start_time * 1_000_000),  # microseconds
            "duration": int(self.duration_ms * 1_000) if self.duration_ms else 0,
            "tags": self.tags,
            "logs": self.logs,
            "processID": self.service,
            "status": self.status,
        }


# ── Metrics Recording ─────────────────────────────────────────────────────────

class MetricType(Enum):
    """Types of metrics for Prometheus."""
    COUNTER = "counter"  # Monotonically increasing
    GAUGE = "gauge"  # Can go up or down
    HISTOGRAM = "histogram"  # Distribution over buckets
    SUMMARY = "summary"  # Percentiles


@dataclass
class Metric:
    """Recorded metric for Prometheus."""
    name: str
    metric_type: MetricType
    value: float
    labels: Dict[str, str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    def to_prometheus_format(self) -> str:
        """Format as Prometheus metrics format."""
        labels_str = "".join(f'{k}="{v}"' for k, v in self.labels.items())
        if labels_str:
            return f'{self.name}{{{labels_str}}} {self.value}'
        return f'{self.name} {self.value}'


class MetricsCollector:
    """Collects and aggregates metrics for Prometheus export."""

    def __init__(self):
        self.metrics = {}  # metric_name -> list of metrics
        self.lock = None  # For thread safety

    def record_counter(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        """Record counter metric (monotonically increasing)."""
        key = f"{name}:{labels or {}}"
        if key not in self.metrics:
            self.metrics[key] = Metric(name, MetricType.COUNTER, 0, labels)
        self.metrics[key].value += value

    def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record gauge metric (can go up/down)."""
        key = f"{name}:{labels or {}}"
        self.metrics[key] = Metric(name, MetricType.GAUGE, value, labels)

    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record histogram metric (distribution)."""
        key = f"{name}:{labels or {}}"
        if key not in self.metrics:
            self.metrics[key] = Metric(name, MetricType.HISTOGRAM, 0, labels)
        # In production, use proper histogram buckets
        self.metrics[key].value += 1

    def get_metrics(self) -> list[str]:
        """Export metrics in Prometheus format."""
        lines = []
        for metric in self.metrics.values():
            lines.append(metric.to_prometheus_format())
        return lines


# Global metrics collector
_metrics_collector = MetricsCollector()


# ── Context Manager for Tracing ───────────────────────────────────────────────

@contextmanager
def trace_span(
    operation: str,
    trace_context: TraceContext,
    tags: Dict[str, Any] = None,
):
    """Context manager for recording spans."""
    import secrets

    span_id = secrets.token_hex(8)
    span = Span(
        trace_id=trace_context.trace_id,
        span_id=span_id,
        operation=operation,
        tags=tags or {},
    )

    try:
        yield span
        span.finish(status="OK")
    except Exception as e:
        span.finish(status="ERROR", error=str(e))
        raise
    finally:
        # In production, send span to Jaeger
        pass


# ── APM Instrumentation ───────────────────────────────────────────────────────

class RequestMetrics:
    """APM metrics for HTTP requests."""

    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_duration_ms = 0

    def record_request(self, duration_ms: float, status_code: int):
        """Record request metrics."""
        self.total_requests += 1
        self.total_duration_ms += duration_ms

        if 200 <= status_code < 400:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # Record to metrics collector
        _metrics_collector.record_counter(
            "http_requests_total",
            labels={"status_code": str(status_code)},
        )
        _metrics_collector.record_histogram(
            "http_request_duration_ms",
            duration_ms,
            labels={"endpoint": "unknown"},
        )

    @property
    def average_duration_ms(self) -> float:
        """Average request duration."""
        return (
            self.total_duration_ms / self.total_requests
            if self.total_requests > 0
            else 0
        )

    @property
    def success_rate(self) -> float:
        """Success rate (0-1)."""
        return (
            self.successful_requests / self.total_requests
            if self.total_requests > 0
            else 0
        )


# Global request metrics
_request_metrics = RequestMetrics()


def get_request_metrics() -> RequestMetrics:
    """Get global request metrics."""
    return _request_metrics


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    return _metrics_collector


def get_structured_logger(name: str) -> StructuredLogger:
    """Get structured logger for module."""
    return StructuredLogger(name)
