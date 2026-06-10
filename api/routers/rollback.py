"""Automatic Rollback API — Self-healing deployments."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from api.db import get_db, User
from api.auth import get_current_user
from api.rollback import (
    RollbackPolicy as RollbackPolicyDC,
    RollbackReason,
    RollbackStatus,
    evaluate_rollback_decision,
    RollbackContext,
    DeploymentVersion,
    can_rollback_now,
    record_rollback,
    update_rollback_status,
    get_rollback_history,
    format_rollback_alert,
)

router = APIRouter(prefix="/rollback", tags=["rollback"])


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/policy")
def get_rollback_policy(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current rollback policy."""
    from api.db import RollbackPolicy

    policy = db.query(RollbackPolicy).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Rollback policy not configured")

    return {
        "id": policy.id,
        "enabled": policy.enabled,
        "error_rate_threshold_percent": policy.error_rate_threshold_percent,
        "latency_threshold_ms": policy.latency_threshold_ms,
        "window_minutes": policy.window_minutes,
        "min_samples": policy.min_samples,
        "cooldown_minutes": policy.cooldown_minutes,
        "require_approval": policy.require_approval,
        "max_rollbacks_per_hour": policy.max_rollbacks_per_hour,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }


@router.patch("/policy")
def update_rollback_policy(
    enabled: Optional[bool] = None,
    error_rate_threshold_percent: Optional[float] = None,
    latency_threshold_ms: Optional[int] = None,
    window_minutes: Optional[int] = None,
    min_samples: Optional[int] = None,
    cooldown_minutes: Optional[int] = None,
    require_approval: Optional[bool] = None,
    max_rollbacks_per_hour: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update rollback policy (admin only)."""
    from api.db import RollbackPolicy

    policy = db.query(RollbackPolicy).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Rollback policy not found")

    if enabled is not None:
        policy.enabled = enabled
    if error_rate_threshold_percent is not None:
        policy.error_rate_threshold_percent = error_rate_threshold_percent
    if latency_threshold_ms is not None:
        policy.latency_threshold_ms = latency_threshold_ms
    if window_minutes is not None:
        policy.window_minutes = window_minutes
    if min_samples is not None:
        policy.min_samples = min_samples
    if cooldown_minutes is not None:
        policy.cooldown_minutes = cooldown_minutes
    if require_approval is not None:
        policy.require_approval = require_approval
    if max_rollbacks_per_hour is not None:
        policy.max_rollbacks_per_hour = max_rollbacks_per_hour

    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(policy)

    return {
        "message": "Rollback policy updated",
        "enabled": policy.enabled,
        "error_rate_threshold_percent": policy.error_rate_threshold_percent,
    }


@router.post("/evaluate")
def evaluate_rollback(
    current_version: str,
    previous_version: str,
    error_rate_current: float,
    error_rate_baseline: float,
    latency_current_ms: float,
    latency_baseline_ms: float,
    error_count: int = 0,
    sample_count: int = 0,
    critical_errors: Optional[list[str]] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate if rollback should be triggered."""
    from api.db import RollbackPolicy

    policy_model = db.query(RollbackPolicy).first()
    if not policy_model:
        raise HTTPException(status_code=404, detail="Rollback policy not configured")

    policy = RollbackPolicyDC(
        enabled=policy_model.enabled,
        error_rate_threshold_percent=policy_model.error_rate_threshold_percent,
        latency_threshold_ms=policy_model.latency_threshold_ms,
        window_minutes=policy_model.window_minutes,
        min_samples=policy_model.min_samples,
        cooldown_minutes=policy_model.cooldown_minutes,
        require_approval=policy_model.require_approval,
        max_rollbacks_per_hour=policy_model.max_rollbacks_per_hour,
    )

    context = RollbackContext(
        current_version=DeploymentVersion(
            version=current_version,
            image_uri="",
            deployed_at=datetime.now(timezone.utc),
            is_stable=False,
            can_rollback_to=True,
        ),
        previous_version=DeploymentVersion(
            version=previous_version,
            image_uri="",
            deployed_at=datetime.now(timezone.utc),
            is_stable=True,
            can_rollback_to=True,
        ),
        error_rate_current=error_rate_current,
        error_rate_baseline=error_rate_baseline,
        latency_current_ms=latency_current_ms,
        latency_baseline_ms=latency_baseline_ms,
        error_count=error_count,
        sample_count=sample_count,
        critical_errors=critical_errors or [],
        reason=RollbackReason.ERROR_RATE_SPIKE,
    )

    decision = evaluate_rollback_decision(context, policy)

    can_rollback, reason = can_rollback_now(db, policy)

    return {
        "should_rollback": decision.should_rollback and can_rollback,
        "severity": decision.severity,
        "confidence": decision.confidence,
        "explanation": decision.explanation,
        "estimated_recovery_seconds": decision.estimated_recovery_time_sec,
        "recommended_action": decision.recommended_action,
        "can_execute_now": can_rollback,
        "cooldown_reason": reason,
        "alert": format_rollback_alert(decision, current_version, previous_version) if decision.should_rollback else None,
    }


@router.post("/execute")
def execute_rollback(
    from_version: str,
    to_version: str,
    reason: str = "error_rate_spike",
    approval_token: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a rollback (or request approval)."""
    from api.db import RollbackPolicy

    policy_model = db.query(RollbackPolicy).first()
    if not policy_model or not policy_model.enabled:
        raise HTTPException(status_code=403, detail="Automatic rollback is disabled")

    policy = RollbackPolicyDC(
        enabled=policy_model.enabled,
        error_rate_threshold_percent=policy_model.error_rate_threshold_percent,
        latency_threshold_ms=policy_model.latency_threshold_ms,
        window_minutes=policy_model.window_minutes,
        min_samples=policy_model.min_samples,
        cooldown_minutes=policy_model.cooldown_minutes,
        require_approval=policy_model.require_approval,
        max_rollbacks_per_hour=policy_model.max_rollbacks_per_hour,
    )

    can_rollback, cooldown_reason = can_rollback_now(db, policy)
    if not can_rollback:
        raise HTTPException(status_code=429, detail=f"Rollback blocked: {cooldown_reason}")

    try:
        rollback_reason = RollbackReason(reason)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid reason: {reason}")

    # Record rollback
    status = RollbackStatus.IN_PROGRESS if not policy.require_approval else RollbackStatus.PENDING
    rollback = record_rollback(
        db,
        from_version=from_version,
        to_version=to_version,
        reason=rollback_reason,
        status=status,
        details={
            "requested_by": user.id,
            "approval_token": approval_token,
        },
    )

    if policy.require_approval and not approval_token:
        return {
            "status": "pending_approval",
            "rollback_id": rollback.id,
            "message": "Approval required for rollback",
            "approval_endpoint": f"/rollback/{rollback.id}/approve",
        }

    return {
        "status": "in_progress",
        "rollback_id": rollback.id,
        "from_version": from_version,
        "to_version": to_version,
        "message": "Rollback initiated",
    }


@router.post("/history")
def record_rollback_completion(
    rollback_id: str,
    status: str,
    details: Optional[dict] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update rollback status (completion, failure, etc.)."""
    try:
        rollback_status = RollbackStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    rollback = update_rollback_status(db, rollback_id, rollback_status, details)
    if not rollback:
        raise HTTPException(status_code=404, detail="Rollback not found")

    return {
        "rollback_id": rollback.id,
        "status": rollback.status,
        "completed_at": rollback.completed_at,
    }


@router.get("/history")
def get_rollback_history_endpoint(
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get rollback history."""
    history = get_rollback_history(db, limit=limit)

    return {
        "total": len(history),
        "rollbacks": [
            {
                "id": r.id,
                "from_version": r.from_version,
                "to_version": r.to_version,
                "reason": r.reason,
                "status": r.status,
                "initiated_at": r.initiated_at,
                "completed_at": r.completed_at,
                "details": r.details,
            }
            for r in history
        ],
    }


@router.post("/{rollback_id}/approve")
def approve_rollback(
    rollback_id: str,
    approval_token: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve pending rollback (for manual approval flow)."""
    from api.db import RollbackHistory

    rollback = db.query(RollbackHistory).filter(RollbackHistory.id == rollback_id).first()
    if not rollback:
        raise HTTPException(status_code=404, detail="Rollback not found")

    if rollback.status != RollbackStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Rollback not pending (status: {rollback.status})",
        )

    # Verify approval token (in production, use proper approval mechanism)
    if rollback.details.get("approval_token") != approval_token:
        raise HTTPException(status_code=403, detail="Invalid approval token")

    rollback = update_rollback_status(db, rollback_id, RollbackStatus.IN_PROGRESS)

    return {
        "message": "Rollback approved and initiated",
        "rollback_id": rollback_id,
        "status": "in_progress",
    }
