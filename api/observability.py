"""
Observability module: Analytics, error tracking, metrics, and structured logging.

Integrates:
- Sentry for error tracking and performance monitoring
- PostHog for product analytics and user behavior tracking
- Prometheus metrics for monitoring
- Structured logging with context
"""

import os
import sentry_sdk
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

try:
    from posthog import Posthog
except ImportError:
    Posthog = None


# ── Analytics & Error Tracking ────────────────────────────────────────────────

posthog_client = None


def set_posthog_client(client):
    """Set the global PostHog client instance."""
    global posthog_client
    posthog_client = client


def set_sentry_user(user_id: str, email: str = None, username: str = None):
    """Set current user context in Sentry for error tracking."""
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "username": username,
    })


def track_event(
    event_name: str,
    user_id: str,
    properties: Optional[Dict[str, Any]] = None,
    groups: Optional[Dict[str, str]] = None,
):
    """
    Track a user event across both PostHog and Sentry.

    Args:
        event_name: Name of the event (e.g., "user_signup", "persona_compiled")
        user_id: User identifier
        properties: Event properties (e.g., {"persona_id": "socrates", "platform": "ios"})
        groups: User groups for PostHog cohort analysis (e.g., {"company": "acme"})
    """
    properties = properties or {}
    groups = groups or {}

    # Track in PostHog
    if posthog_client:
        try:
            posthog_client.capture(
                distinct_id=user_id,
                event=event_name,
                properties=properties,
            )
            # Set group properties if provided
            for group_key, group_id in groups.items():
                posthog_client.group(
                    group_key=group_key,
                    group_id=group_id,
                    properties=properties,
                )
        except Exception as e:
            # Graceful degradation: don't break request on analytics error
            logging.warning(f"PostHog tracking failed: {e}")

    # Track in Sentry (as breadcrumb for error context)
    sentry_sdk.capture_message(
        f"Event: {event_name}",
        level="info",
        tags={**groups},
        extra=properties,
    )


def track_checkout(user_id: str, persona_id: str, amount_usd: float):
    """Track a checkout event."""
    track_event(
        "checkout_initiated",
        user_id,
        properties={
            "persona_id": persona_id,
            "amount_usd": amount_usd,
        },
    )


def track_purchase(user_id: str, persona_id: str, amount_usd: float):
    """Track a successful purchase."""
    track_event(
        "persona_purchased",
        user_id,
        properties={
            "persona_id": persona_id,
            "amount_usd": amount_usd,
        },
    )


def track_compilation(user_id: str, persona_id: str, platform: str):
    """Track a persona compilation."""
    track_event(
        "persona_compiled",
        user_id,
        properties={
            "persona_id": persona_id,
            "platform": platform,
        },
    )


def track_signup(user_id: str, email: str, auth_method: str = "email"):
    """Track user signup."""
    set_sentry_user(user_id, email)
    track_event(
        "user_signup",
        user_id,
        properties={
            "email": email,
            "auth_method": auth_method,
        },
    )


def track_error(
    error_message: str,
    user_id: Optional[str] = None,
    error_type: str = "unknown",
    context: Optional[Dict[str, Any]] = None,
):
    """
    Track an error event.

    Args:
        error_message: Description of the error
        user_id: User ID (if applicable)
        error_type: Category of error (e.g., "payment_error", "compilation_error")
        context: Additional context about the error
    """
    if user_id:
        set_sentry_user(user_id)

    track_event(
        "error_occurred",
        user_id or "anonymous",
        properties={
            "error_message": error_message,
            "error_type": error_type,
            **(context or {}),
        },
    )


def capture_exception(exception: Exception, tags: Optional[Dict[str, str]] = None, extra: Optional[Dict[str, Any]] = None):
    """Manually capture an exception in Sentry."""
    sentry_sdk.capture_exception(
        exception,
        tags=tags or {},
        extra=extra or {},
    )


# ── Metrics Collection ────────────────────────────────────────────────────────

@dataclass
class Metric:
    """A single metric data point."""
    name: str
    value: float
    metric_type: str  # "counter", "gauge", "histogram", "summary"
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class RequestMetrics:
    """Aggregated request metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_duration_ms: float = 0.0
    success_rate: float = 1.0


@dataclass
class Span:
    """A distributed trace span."""
    trace_id: str
    span_id: str
    operation: str
    tags: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "OK"  # "OK", "ERROR", "CANCELLED"
    error: Optional[str] = None


class MetricsCollector:
    """Collects and manages application metrics."""

    def __init__(self):
        self.metrics: Dict[str, Metric] = {}

    def record_counter(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a counter metric."""
        key = f"{name}:{labels or {}}"
        self.metrics[key] = Metric(name, value, "counter", labels or {})

    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a gauge metric."""
        key = f"{name}:{labels or {}}"
        self.metrics[key] = Metric(name, value, "gauge", labels or {})

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram metric."""
        key = f"{name}:{labels or {}}"
        self.metrics[key] = Metric(name, value, "histogram", labels or {})

    def get_metrics(self) -> list:
        """Get all metrics."""
        return [m.__dict__ for m in self.metrics.values()]


# Global metrics collector instance
_metrics_collector = MetricsCollector()
_request_metrics = RequestMetrics()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    return _metrics_collector


def get_request_metrics() -> RequestMetrics:
    """Get aggregated request metrics."""
    return _request_metrics


def record_request_metric(status_code: int, duration_ms: float):
    """Record metrics for a completed request."""
    _request_metrics.total_requests += 1
    if 200 <= status_code < 300:
        _request_metrics.successful_requests += 1
    else:
        _request_metrics.failed_requests += 1

    # Update average duration (simple moving average)
    if _request_metrics.total_requests == 1:
        _request_metrics.average_duration_ms = duration_ms
    else:
        _request_metrics.average_duration_ms = (
            (_request_metrics.average_duration_ms * (_request_metrics.total_requests - 1) + duration_ms)
            / _request_metrics.total_requests
        )

    _request_metrics.success_rate = (
        _request_metrics.successful_requests / _request_metrics.total_requests
        if _request_metrics.total_requests > 0
        else 1.0
    )


# ── Structured Logging ────────────────────────────────────────────────────────

class StructuredLogger:
    """Structured logger with context support."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def debug(self, message: str, **context):
        self.logger.debug(f"{message} | {context}")

    def info(self, message: str, **context):
        self.logger.info(f"{message} | {context}")

    def warning(self, message: str, **context):
        self.logger.warning(f"{message} | {context}")

    def error(self, message: str, **context):
        self.logger.error(f"{message} | {context}")


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)
