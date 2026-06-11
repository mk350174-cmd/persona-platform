"""
Analytics Router — Persona Platform
=====================================
REST endpoints for usage analytics, revenue reporting, DAU/MAU metrics,
cohort retention, and CSV data exports.

All endpoints require authentication (X-API-Key / Bearer token).
Admin-only endpoints additionally check user.role == "admin".
"""

from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db, User
from api.analytics import (
    DashboardSummary,
    PersonaUsageStats,
    UserEngagementStats,
    RevenueReport,
    get_dashboard_summary,
    get_persona_usage_stats,
    get_top_personas,
    get_user_engagement,
    get_revenue_report,
    get_daily_active_users,
    get_cohort_retention,
    export_revenue_csv,
    export_dau_csv,
    export_top_personas_csv,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _require_admin(user: User) -> None:
    """Raise 403 if the authenticated user does not hold the admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required.",
        )


def _dataclass_to_dict(obj) -> dict:
    """Shallow dict conversion for dataclass objects (avoids dataclasses.asdict recursion)."""
    return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    summary="Platform dashboard summary",
    response_description="High-level KPIs: users, personas, revenue, MRR.",
)
def dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return a high-level platform snapshot.

    **Admin only.**

    Includes:
    - Total and active user counts (7-day, 30-day windows)
    - Total personas in the catalog
    - Total purchases and aggregate revenue
    - Monthly Recurring Revenue (MRR)
    - Top 10 personas by purchase count
    - New signups in the last 24 hours
    """
    _require_admin(user)
    summary: DashboardSummary = get_dashboard_summary(db)
    return {
        "total_users": summary.total_users,
        "active_users_7d": summary.active_users_7d,
        "active_users_30d": summary.active_users_30d,
        "total_personas": summary.total_personas,
        "total_purchases": summary.total_purchases,
        "total_revenue_usd": summary.total_revenue_usd,
        "mrr": summary.mrr,
        "top_personas": summary.top_personas,
        "recent_signups": summary.recent_signups,
    }


# ── Persona analytics ─────────────────────────────────────────────────────────

@router.get(
    "/personas/top",
    summary="Top personas by usage",
    response_description="Ranked list of personas with usage and revenue stats.",
)
def top_personas(
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of personas to return."),
    days: int = Query(default=30, ge=1, le=365, description="Look-back window in days."),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the most-used personas in the specified time window.

    **Admin only.**

    Results are ranked by total API call volume. Falls back to purchase counts
    when no API usage data is available (e.g. on a fresh installation).
    """
    _require_admin(user)
    personas = get_top_personas(db, limit=limit, days=days)
    return {
        "personas": [
            {
                "persona_id": p.persona_id,
                "total_conversations": p.total_conversations,
                "total_messages": p.total_messages,
                "unique_users": p.unique_users,
                "avg_session_length": p.avg_session_length,
                "revenue_usd": p.revenue_usd,
            }
            for p in personas
        ],
        "limit": limit,
        "days": days,
        "count": len(personas),
    }


@router.get(
    "/personas/{persona_id}",
    summary="Single persona usage stats",
    response_description="Usage and revenue breakdown for one persona.",
)
def persona_stats(
    persona_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Look-back window in days."),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return detailed usage statistics for a specific persona.

    **Admin only.**

    Includes total API calls, unique users, estimated sessions, average
    session length, and all-time purchase revenue.
    """
    _require_admin(user)
    stats: PersonaUsageStats = get_persona_usage_stats(db, persona_id=persona_id, days=days)
    return {
        "persona_id": stats.persona_id,
        "total_conversations": stats.total_conversations,
        "total_messages": stats.total_messages,
        "unique_users": stats.unique_users,
        "avg_session_length": stats.avg_session_length,
        "revenue_usd": stats.revenue_usd,
        "days": days,
    }


# ── User engagement ───────────────────────────────────────────────────────────

@router.get(
    "/users/{user_id}",
    summary="User engagement statistics",
    response_description="Message counts, sessions, favourite persona, and retention.",
)
def user_engagement(
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return engagement metrics for a user.

    Users may only view their **own** stats. Admins may query any user.

    Metrics returned:
    - total_sessions: distinct active days
    - total_messages: total API calls
    - favorite_persona: most-used persona
    - avg_daily_messages: messages per active day
    - retention_days: span from first to last usage event
    - tier: current subscription tier (or "free")
    """
    # Authorization: self or admin
    if user.id != user_id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own engagement stats.",
        )

    stats: UserEngagementStats = get_user_engagement(db, user_id=user_id)
    return {
        "user_id": stats.user_id,
        "total_sessions": stats.total_sessions,
        "total_messages": stats.total_messages,
        "favorite_persona": stats.favorite_persona,
        "avg_daily_messages": stats.avg_daily_messages,
        "retention_days": stats.retention_days,
        "tier": stats.tier,
    }


# ── Revenue report ─────────────────────────────────────────────────────────────

@router.get(
    "/revenue",
    summary="Revenue report",
    response_description="Revenue totals, MRR, ARPU, and subscriber churn.",
)
def revenue_report(
    period: str = Query(
        default="monthly",
        pattern="^(daily|weekly|monthly)$",
        description="Report period: 'daily', 'weekly', or 'monthly'.",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return a revenue report for the specified period.

    **Admin only.**

    Metrics:
    - **total_revenue_usd**: sum of all purchases in window
    - **new_subscribers**: new subscriptions created in window
    - **churned_subscribers**: subscriptions cancelled in window
    - **mrr**: Monthly Recurring Revenue from active subscriptions
    - **arpu**: Average Revenue Per User (MRR / active subscriber count)
    - **top_personas**: top 10 personas by revenue in window
    """
    _require_admin(user)
    report: RevenueReport = get_revenue_report(db, period=period)
    return {
        "period": report.period,
        "total_revenue_usd": report.total_revenue_usd,
        "new_subscribers": report.new_subscribers,
        "churned_subscribers": report.churned_subscribers,
        "mrr": report.mrr,
        "arpu": report.arpu,
        "top_personas": report.top_personas,
    }


# ── Daily active users ─────────────────────────────────────────────────────────

@router.get(
    "/dau",
    summary="Daily active users time series",
    response_description="Day-by-day unique active user counts.",
)
def daily_active_users(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to include."),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return a daily active user (DAU) time series.

    **Admin only.**

    Each entry is `{"date": "YYYY-MM-DD", "count": <int>}`.
    Dates with no activity are included with count = 0.
    """
    _require_admin(user)
    series = get_daily_active_users(db, days=days)
    return {
        "days": days,
        "series": series,
        "total_data_points": len(series),
    }


# ── Cohort retention ───────────────────────────────────────────────────────────

@router.get(
    "/retention",
    summary="Cohort retention analysis",
    response_description="Month-over-month retention rates for a signup cohort.",
)
def cohort_retention(
    month: str = Query(
        default=...,
        description="Cohort month in YYYY-MM format, e.g. '2024-06'.",
        pattern=r"^\d{4}-\d{2}$",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compute cohort retention for users who signed up in `month`.

    **Admin only.**

    Response includes:
    - **cohort_size**: number of users in the cohort
    - **retention**: dict of `month_N → user count` (N = months since signup)
    - **retention_rates**: dict of `month_N → retention fraction` (0.0–1.0)
    """
    _require_admin(user)
    result = get_cohort_retention(db, cohort_month=month)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


# ── CSV exports ────────────────────────────────────────────────────────────────

@router.get(
    "/export/csv",
    summary="Download analytics as CSV",
    response_description="CSV file download.",
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "CSV data stream.",
        }
    },
)
def export_csv(
    type: str = Query(
        default="revenue",
        pattern="^(revenue|dau|top_personas)$",
        description="Export type: 'revenue', 'dau', or 'top_personas'.",
    ),
    period: str = Query(
        default="monthly",
        pattern="^(daily|weekly|monthly)$",
        description="Period for revenue exports.",
    ),
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Look-back window for dau/top_personas exports.",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Max rows for top_personas export.",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export analytics data as a downloadable CSV file.

    **Admin only.**

    Supported export types:
    - **revenue**: Revenue report with top personas breakdown
    - **dau**: Daily active users time series
    - **top_personas**: Top personas by usage volume

    The response is streamed as `text/csv` with a `Content-Disposition` header
    for direct download from a browser or `curl -O`.
    """
    _require_admin(user)

    if type == "revenue":
        csv_data = export_revenue_csv(db, period=period)
        filename = f"revenue_{period}.csv"
    elif type == "dau":
        csv_data = export_dau_csv(db, days=days)
        filename = f"dau_{days}d.csv"
    elif type == "top_personas":
        csv_data = export_top_personas_csv(db, limit=limit, days=days)
        filename = f"top_personas_{days}d.csv"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown export type: {type}",
        )

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
