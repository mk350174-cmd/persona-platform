"""
Automatic Rollback Service — Self-healing deployments

Monitors error rates and automatically reverts to previous version if:
- Error rate spikes above threshold
- Critical errors detected
- Health checks fail
"""

from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session


class RollbackReason(Enum):
    """Reasons for automatic rollback."""
    ERROR_RATE_SPIKE = "error_rate_spike"
    LATENCY_DEGRADATION = "latency_degradation"
    HEALTH_CHECK_FAILED = "health_check_failed"
    CRITICAL_ERROR = "critical_error"
    MANUAL_TRIGGER = "manual_trigger"


class RollbackStatus(Enum):
    """Status of rollback execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RollbackPolicy:
    """Configuration for automatic rollbacks."""
    enabled: bool
    error_rate_threshold_percent: float  # e.g., 2.0 for 2% error rate
    latency_threshold_ms: int  # e.g., 500ms for p95 latency
    window_minutes: int  # Look-back window for metrics
    min_samples: int  # Minimum samples before triggering rollback
    cooldown_minutes: int  # Don't rollback again within this period
    require_approval: bool  # Manual approval before rollback
    max_rollbacks_per_hour: int  # Prevent rollback loops


@dataclass
class DeploymentVersion:
    """Deployment version info."""
    version: str  # e.g., "1.2.3" or "abc123def456"
    image_uri: str  # e.g., "ghcr.io/mk350174/persona-platform:1.2.3"
    deployed_at: datetime
    is_stable: bool  # Previously verified as stable
    can_rollback_to: bool  # Is rollback target available


@dataclass
class RollbackContext:
    """Context for rollback decision."""
    current_version: DeploymentVersion
    previous_version: DeploymentVersion
    error_rate_current: float
    error_rate_baseline: float
    latency_current_ms: float
    latency_baseline_ms: float
    error_count: int
    sample_count: int
    critical_errors: list[str]
    reason: RollbackReason


@dataclass
class RollbackDecision:
    """Decision to rollback or not."""
    should_rollback: bool
    severity: str  # "critical", "high", "medium", "low"
    confidence: float  # 0.0-1.0
    explanation: str
    estimated_recovery_time_sec: int
    recommended_action: str


# ── Rollback Detection ────────────────────────────────────────────────────────


def detect_error_rate_spike(
    current_error_rate: float,
    baseline_error_rate: float,
    spike_threshold_percent: float = 150.0,  # 150% increase = 1.5x
) -> tuple[bool, float]:
    """Detect if error rate spiked significantly.

    Returns: (is_spike, percent_increase)
    """
    if baseline_error_rate == 0:
        # If baseline is 0 (no errors), any error is a spike
        return current_error_rate > 0.1, float('inf')

    percent_increase = ((current_error_rate - baseline_error_rate) / baseline_error_rate) * 100
    is_spike = percent_increase >= spike_threshold_percent

    return is_spike, percent_increase


def detect_latency_spike(
    current_latency_ms: float,
    baseline_latency_ms: float,
    spike_threshold_percent: float = 50.0,  # 50% increase
) -> tuple[bool, float]:
    """Detect if latency degraded significantly.

    Returns: (is_spike, percent_increase)
    """
    if baseline_latency_ms == 0:
        return current_latency_ms > 100, float('inf')

    percent_increase = ((current_latency_ms - baseline_latency_ms) / baseline_latency_ms) * 100
    is_spike = percent_increase >= spike_threshold_percent

    return is_spike, percent_increase


def evaluate_rollback_decision(
    context: RollbackContext,
    policy: RollbackPolicy,
) -> RollbackDecision:
    """Evaluate whether to rollback based on metrics and policy.

    Returns detailed decision with confidence and explanation.
    """
    reasons = []
    severity_scores = []

    # Check error rate
    error_spike, error_percent = detect_error_rate_spike(
        context.error_rate_current,
        context.error_rate_baseline,
    )
    if error_spike and context.error_rate_current > policy.error_rate_threshold_percent:
        reasons.append(f"Error rate spiked by {error_percent:.1f}% (now {context.error_rate_current:.1f}%)")
        severity_scores.append(0.9)

    # Check latency
    latency_spike, latency_percent = detect_latency_spike(
        context.latency_current_ms,
        context.latency_baseline_ms,
    )
    if latency_spike and context.latency_current_ms > policy.latency_threshold_ms:
        reasons.append(f"Latency degraded by {latency_percent:.1f}% (now {context.latency_current_ms:.0f}ms)")
        severity_scores.append(0.7)

    # Check critical errors
    if context.critical_errors:
        reasons.append(f"Critical errors detected: {len(context.critical_errors)}")
        severity_scores.append(0.95)

    # Check minimum samples
    if context.sample_count < policy.min_samples:
        reasons.append(f"Insufficient samples ({context.sample_count}/{policy.min_samples})")
        severity_scores.append(-0.2)  # Reduce confidence

    # Determine if should rollback
    should_rollback = (
        len(reasons) > 0
        and all(score >= 0 for score in severity_scores)
        and max(severity_scores) >= 0.7
    )

    if not should_rollback:
        return RollbackDecision(
            should_rollback=False,
            severity="low",
            confidence=0.0,
            explanation="Metrics within acceptable range",
            estimated_recovery_time_sec=0,
            recommended_action="Continue monitoring",
        )

    # Calculate confidence (0-1)
    confidence = min(1.0, sum(severity_scores) / len(severity_scores))

    # Determine severity
    if any(score >= 0.9 for score in severity_scores):
        severity = "critical"
    elif any(score >= 0.7 for score in severity_scores):
        severity = "high"
    else:
        severity = "medium"

    explanation = "\n".join(f"• {r}" for r in reasons)

    return RollbackDecision(
        should_rollback=True,
        severity=severity,
        confidence=confidence,
        explanation=explanation,
        estimated_recovery_time_sec=120,  # ~2 minutes
        recommended_action=_get_rollback_action(severity),
    )


def _get_rollback_action(severity: str) -> str:
    """Get recommended action based on severity."""
    if severity == "critical":
        return "URGENT: Initiate automatic rollback immediately"
    elif severity == "high":
        return "Request manual approval for rollback (auto-rollback if no response in 2 min)"
    else:
        return "Log incident, monitor metrics closely, prepare rollback if trend continues"


# ── Rollback Tracking ─────────────────────────────────────────────────────────


def can_rollback_now(
    db: Session,
    policy: RollbackPolicy,
) -> tuple[bool, Optional[str]]:
    """Check if rollback is allowed now (respects cooldown period).

    Returns: (can_rollback, reason_if_no)
    """
    from api.db import RollbackHistory

    # Check recent rollbacks
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=policy.cooldown_minutes)
    recent = db.query(RollbackHistory).filter(
        RollbackHistory.completed_at >= cutoff,
        RollbackHistory.status == RollbackStatus.COMPLETED.value,
    ).count()

    if recent > 0:
        return False, f"Rollback in cooldown period ({policy.cooldown_minutes} min)"

    # Check rollback rate
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    last_hour = db.query(RollbackHistory).filter(
        RollbackHistory.completed_at >= one_hour_ago,
        RollbackHistory.status == RollbackStatus.COMPLETED.value,
    ).count()

    if last_hour >= policy.max_rollbacks_per_hour:
        return False, f"Max rollbacks per hour exceeded ({last_hour}/{policy.max_rollbacks_per_hour})"

    return True, None


def record_rollback(
    db: Session,
    from_version: str,
    to_version: str,
    reason: RollbackReason,
    status: RollbackStatus = RollbackStatus.PENDING,
    details: Optional[dict] = None,
) -> "RollbackHistory":
    """Record a rollback attempt in database."""
    from api.db import RollbackHistory
    import secrets

    rollback = RollbackHistory(
        id=f"rollback_{secrets.token_hex(8)}",
        from_version=from_version,
        to_version=to_version,
        reason=reason.value,
        status=status.value,
        details=details or {},
        initiated_at=datetime.now(timezone.utc),
    )
    db.add(rollback)
    db.commit()
    db.refresh(rollback)
    return rollback


def update_rollback_status(
    db: Session,
    rollback_id: str,
    status: RollbackStatus,
    details: Optional[dict] = None,
) -> Optional["RollbackHistory"]:
    """Update rollback status."""
    from api.db import RollbackHistory

    rollback = db.query(RollbackHistory).filter(RollbackHistory.id == rollback_id).first()
    if not rollback:
        return None

    rollback.status = status.value
    if details:
        rollback.details = {**(rollback.details or {}), **details}

    if status == RollbackStatus.COMPLETED:
        rollback.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(rollback)
    return rollback


def get_rollback_history(
    db: Session,
    limit: int = 50,
) -> list["RollbackHistory"]:
    """Get recent rollback history."""
    from api.db import RollbackHistory

    return db.query(RollbackHistory).order_by(
        RollbackHistory.initiated_at.desc()
    ).limit(limit).all()


# ── Rollback Execution ────────────────────────────────────────────────────────


def format_rollback_alert(
    decision: RollbackDecision,
    current_version: str,
    previous_version: str,
) -> dict:
    """Format rollback decision for alerting."""
    severity_emoji = {
        "critical": "🚨",
        "high": "⚠️",
        "medium": "⚡",
        "low": "ℹ️",
    }

    return {
        "title": f"{severity_emoji[decision.severity]} Automatic Rollback Triggered",
        "severity": decision.severity.upper(),
        "from_version": current_version,
        "to_version": previous_version,
        "estimated_recovery": f"{decision.estimated_recovery_time_sec}s",
        "explanation": decision.explanation,
        "confidence": f"{decision.confidence * 100:.0f}%",
        "action": decision.recommended_action,
        "manual_rollback_command": (
            f"gh run cancel $(gh run list --workflow=deploy | head -1 | awk '{{print $7}}')\n"
            f"git revert HEAD && git push origin main"
        ),
    }


def get_previous_stable_version(
    db: Session,
) -> Optional[str]:
    """Get most recent known stable version."""
    from api.db import RollbackHistory

    stable = db.query(RollbackHistory).filter(
        RollbackHistory.status == RollbackStatus.COMPLETED.value,
    ).order_by(
        RollbackHistory.completed_at.desc()
    ).first()

    return stable.to_version if stable else None
