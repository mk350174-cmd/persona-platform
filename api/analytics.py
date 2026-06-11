"""
Analytics Engine — Persona Platform
=====================================
Aggregated metrics for personas, users, revenue, and engagement.

All queries use SQLAlchemy aggregate functions (func.count, func.sum, func.avg)
rather than Python-side loops for performance at scale.

Usage:
    from api.analytics import get_dashboard_summary, get_revenue_report
    summary = get_dashboard_summary(db)
    report  = get_revenue_report(db, period="monthly")
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, distinct, case
from sqlalchemy.orm import Session

from api.db import (
    User,
    Purchase,
    Subscription,
    APIKeyUsage,
    SUBSCRIPTION_TIERS,
)


# ── Data Classes ──────────────────────────────────────────────────────────────


@dataclass
class PersonaUsageStats:
    """Usage statistics for a single persona over a time window."""
    persona_id: str
    total_conversations: int        # distinct API call sessions
    total_messages: int             # total API calls hitting this persona
    unique_users: int               # distinct users who used the persona
    avg_session_length: float       # avg messages per unique user
    revenue_usd: float              # total purchase revenue in USD


@dataclass
class UserEngagementStats:
    """Engagement statistics for a single user."""
    user_id: str
    total_sessions: int             # distinct days with activity (proxy for sessions)
    total_messages: int             # total API calls made
    favorite_persona: str           # persona_id most used
    avg_daily_messages: float       # messages / active days
    retention_days: int             # days between first and last activity
    tier: str                       # subscription tier or "free"


@dataclass
class RevenueReport:
    """Revenue aggregation for a billing period."""
    period: str                     # "daily" | "weekly" | "monthly"
    total_revenue_usd: float        # sum of all purchase amounts
    new_subscribers: int            # new subscriptions in period
    churned_subscribers: int        # cancelled subscriptions in period
    mrr: float                      # Monthly Recurring Revenue (USD)
    arpu: float                     # Average Revenue Per User (USD)
    top_personas: list[dict]        # [{persona_id, revenue, purchases}]


@dataclass
class DashboardSummary:
    """High-level platform KPIs for the admin dashboard."""
    total_users: int
    active_users_7d: int
    active_users_30d: int
    total_personas: int             # distinct persona_ids ever purchased or used
    total_purchases: int
    total_revenue_usd: float
    mrr: float
    top_personas: list[dict]        # [{persona_id, purchases, revenue_usd}]
    recent_signups: int             # users created in last 24 h


# ── Internal helpers ──────────────────────────────────────────────────────────


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _window_start(days: int) -> datetime:
    """Return a timezone-aware datetime `days` ago."""
    return _utc_now() - timedelta(days=days)


def _naive(dt: datetime) -> datetime:
    """Strip timezone info for SQLite comparisons (SQLite stores naive datetimes)."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _cents_to_usd(cents: int | None) -> float:
    """Convert integer cents to a float USD value. None → 0.0."""
    if cents is None:
        return 0.0
    return round(cents / 100, 2)


def _calculate_mrr(db: Session) -> float:
    """
    Estimate Monthly Recurring Revenue from active subscriptions.

    Uses SUBSCRIPTION_TIERS pricing:
      - monthly tiers  → price_usd / 1  per month
      - annual tiers   → price_usd / 12 per month
    """
    active_subs = (
        db.query(Subscription.tier, func.count(Subscription.id).label("count"))
        .filter(
            Subscription.status == "active",
            Subscription.deleted_at == None,
        )
        .group_by(Subscription.tier)
        .all()
    )

    mrr = 0.0
    for tier_name, count in active_subs:
        cfg = SUBSCRIPTION_TIERS.get(tier_name, {})
        price = cfg.get("price_usd", 0.0)
        billing = cfg.get("billing_period", "month")
        if billing == "year":
            mrr += (price / 12) * count
        else:
            mrr += price * count

    return round(mrr, 2)


# ── Core Analytics Functions ──────────────────────────────────────────────────


def get_dashboard_summary(db: Session) -> DashboardSummary:
    """
    Compute all top-level KPIs in a small number of SQL queries.
    Safe on empty databases — all aggregates fall back to 0 / [].
    """
    now_naive = _naive(_utc_now())
    window_7d  = _naive(_window_start(7))
    window_30d = _naive(_window_start(30))
    window_24h = _naive(_window_start(1))

    # ── User counts ──
    total_users = (
        db.query(func.count(User.id))
        .filter(User.deleted_at == None)
        .scalar() or 0
    )

    recent_signups = (
        db.query(func.count(User.id))
        .filter(
            User.deleted_at == None,
            User.created_at >= window_24h,
        )
        .scalar() or 0
    )

    # Active users: distinct users with API usage in window
    active_users_7d = (
        db.query(func.count(distinct(APIKeyUsage.user_id)))
        .filter(APIKeyUsage.timestamp >= window_7d)
        .scalar() or 0
    )

    active_users_30d = (
        db.query(func.count(distinct(APIKeyUsage.user_id)))
        .filter(APIKeyUsage.timestamp >= window_30d)
        .scalar() or 0
    )

    # ── Purchase counts & revenue ──
    total_purchases = (
        db.query(func.count(Purchase.id))
        .filter(Purchase.deleted_at == None)
        .scalar() or 0
    )

    revenue_cents = (
        db.query(func.sum(Purchase.amount_usd))
        .filter(Purchase.deleted_at == None)
        .scalar() or 0
    )
    total_revenue_usd = _cents_to_usd(revenue_cents)

    # ── Distinct personas ──
    # Count from both purchases and API usage logs
    purchased_ids = (
        db.query(func.count(distinct(Purchase.persona_id)))
        .filter(Purchase.deleted_at == None)
        .scalar() or 0
    )
    used_ids = (
        db.query(func.count(distinct(APIKeyUsage.persona_id)))
        .filter(APIKeyUsage.persona_id != None)
        .scalar() or 0
    )
    # Use the larger of the two as the "total known personas"
    total_personas = max(purchased_ids, used_ids)

    # ── Top personas (by purchase count) ──
    top_rows = (
        db.query(
            Purchase.persona_id,
            func.count(Purchase.id).label("purchases"),
            func.sum(Purchase.amount_usd).label("revenue_cents"),
        )
        .filter(Purchase.deleted_at == None)
        .group_by(Purchase.persona_id)
        .order_by(func.count(Purchase.id).desc())
        .limit(10)
        .all()
    )

    top_personas = [
        {
            "persona_id": row.persona_id,
            "purchases": row.purchases,
            "revenue_usd": _cents_to_usd(row.revenue_cents),
        }
        for row in top_rows
    ]

    mrr = _calculate_mrr(db)

    return DashboardSummary(
        total_users=total_users,
        active_users_7d=active_users_7d,
        active_users_30d=active_users_30d,
        total_personas=total_personas,
        total_purchases=total_purchases,
        total_revenue_usd=total_revenue_usd,
        mrr=mrr,
        top_personas=top_personas,
        recent_signups=recent_signups,
    )


def get_persona_usage_stats(
    db: Session,
    persona_id: str,
    days: int = 30,
) -> PersonaUsageStats:
    """
    Return usage statistics for a single persona over the last `days` days.
    Revenue is derived from Purchase.amount_usd (all time, not windowed).
    """
    window = _naive(_window_start(days))

    # Usage within window
    usage_row = (
        db.query(
            func.count(APIKeyUsage.id).label("total_messages"),
            func.count(distinct(APIKeyUsage.user_id)).label("unique_users"),
        )
        .filter(
            APIKeyUsage.persona_id == persona_id,
            APIKeyUsage.timestamp >= window,
        )
        .first()
    )

    total_messages = (usage_row.total_messages or 0) if usage_row else 0
    unique_users   = (usage_row.unique_users or 0) if usage_row else 0

    # Estimate conversations = unique users (one session per user per time window)
    # More precise: count distinct (user_id, date(timestamp)) pairs
    total_conversations = unique_users

    avg_session_length = (
        round(total_messages / unique_users, 2)
        if unique_users > 0
        else 0.0
    )

    # All-time revenue for this persona
    revenue_cents = (
        db.query(func.sum(Purchase.amount_usd))
        .filter(
            Purchase.persona_id == persona_id,
            Purchase.deleted_at == None,
        )
        .scalar() or 0
    )

    return PersonaUsageStats(
        persona_id=persona_id,
        total_conversations=total_conversations,
        total_messages=total_messages,
        unique_users=unique_users,
        avg_session_length=avg_session_length,
        revenue_usd=_cents_to_usd(revenue_cents),
    )


def get_top_personas(
    db: Session,
    limit: int = 10,
    days: int = 30,
) -> list[PersonaUsageStats]:
    """
    Return the top `limit` personas ranked by total API usage in the window.
    Falls back gracefully to purchase data if usage logs are empty.
    """
    window = _naive(_window_start(days))

    top_rows = (
        db.query(
            APIKeyUsage.persona_id,
            func.count(APIKeyUsage.id).label("total_messages"),
            func.count(distinct(APIKeyUsage.user_id)).label("unique_users"),
        )
        .filter(
            APIKeyUsage.persona_id != None,
            APIKeyUsage.timestamp >= window,
        )
        .group_by(APIKeyUsage.persona_id)
        .order_by(func.count(APIKeyUsage.id).desc())
        .limit(limit)
        .all()
    )

    if not top_rows:
        # Fall back: top personas by purchase count (all time)
        purchase_rows = (
            db.query(
                Purchase.persona_id,
                func.count(Purchase.id).label("total_messages"),
                func.count(distinct(Purchase.user_id)).label("unique_users"),
                func.sum(Purchase.amount_usd).label("revenue_cents"),
            )
            .filter(Purchase.deleted_at == None)
            .group_by(Purchase.persona_id)
            .order_by(func.count(Purchase.id).desc())
            .limit(limit)
            .all()
        )
        return [
            PersonaUsageStats(
                persona_id=row.persona_id,
                total_conversations=row.unique_users or 0,
                total_messages=row.total_messages or 0,
                unique_users=row.unique_users or 0,
                avg_session_length=0.0,
                revenue_usd=_cents_to_usd(row.revenue_cents),
            )
            for row in purchase_rows
        ]

    # Enrich each row with revenue data via a single grouped query
    persona_ids = [r.persona_id for r in top_rows]
    revenue_rows = (
        db.query(
            Purchase.persona_id,
            func.sum(Purchase.amount_usd).label("revenue_cents"),
        )
        .filter(
            Purchase.persona_id.in_(persona_ids),
            Purchase.deleted_at == None,
        )
        .group_by(Purchase.persona_id)
        .all()
    )
    revenue_map = {r.persona_id: r.revenue_cents or 0 for r in revenue_rows}

    result = []
    for row in top_rows:
        total_messages = row.total_messages or 0
        unique_users   = row.unique_users or 0
        result.append(
            PersonaUsageStats(
                persona_id=row.persona_id,
                total_conversations=unique_users,
                total_messages=total_messages,
                unique_users=unique_users,
                avg_session_length=(
                    round(total_messages / unique_users, 2)
                    if unique_users > 0
                    else 0.0
                ),
                revenue_usd=_cents_to_usd(revenue_map.get(row.persona_id, 0)),
            )
        )
    return result


def get_user_engagement(db: Session, user_id: str) -> UserEngagementStats:
    """
    Return engagement statistics for a single user.
    Uses APIKeyUsage for message counts and date-based session estimation.
    """
    # Total messages
    total_messages = (
        db.query(func.count(APIKeyUsage.id))
        .filter(APIKeyUsage.user_id == user_id)
        .scalar() or 0
    )

    # Favorite persona: most-used persona_id
    fav_row = (
        db.query(
            APIKeyUsage.persona_id,
            func.count(APIKeyUsage.id).label("cnt"),
        )
        .filter(
            APIKeyUsage.user_id == user_id,
            APIKeyUsage.persona_id != None,
        )
        .group_by(APIKeyUsage.persona_id)
        .order_by(func.count(APIKeyUsage.id).desc())
        .first()
    )
    favorite_persona = fav_row.persona_id if fav_row else ""

    # First and last usage timestamps (for retention calculation)
    bounds = (
        db.query(
            func.min(APIKeyUsage.timestamp).label("first_ts"),
            func.max(APIKeyUsage.timestamp).label("last_ts"),
        )
        .filter(APIKeyUsage.user_id == user_id)
        .first()
    )

    if bounds and bounds.first_ts and bounds.last_ts:
        first_ts = bounds.first_ts
        last_ts  = bounds.last_ts
        # Handle both naive and timezone-aware datetimes
        if hasattr(first_ts, "tzinfo") and first_ts.tzinfo is None:
            retention_days = (last_ts - first_ts).days
        else:
            retention_days = (last_ts - first_ts).days
        retention_days = max(retention_days, 0)
    else:
        retention_days = 0

    # Total sessions: distinct calendar days with any usage
    # SQLite: strftime('%Y-%m-%d', timestamp)
    # PostgreSQL: DATE(timestamp)
    # We use a Python-side approach that works for both — count distinct dates
    # via a subquery casting timestamp to date string
    from sqlalchemy import cast, Date as SADate
    from sqlalchemy import text as sa_text

    try:
        # Works on PostgreSQL
        total_sessions = (
            db.query(func.count(distinct(cast(APIKeyUsage.timestamp, SADate))))
            .filter(APIKeyUsage.user_id == user_id)
            .scalar() or 0
        )
    except Exception:
        # Fallback: count all rows / average (rough approximation)
        total_sessions = max(total_messages // 5, 1) if total_messages > 0 else 0

    avg_daily_messages = (
        round(total_messages / total_sessions, 2)
        if total_sessions > 0
        else 0.0
    )

    # Subscription tier
    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.deleted_at == None,
        )
        .first()
    )
    tier = sub.tier if sub else "free"

    return UserEngagementStats(
        user_id=user_id,
        total_sessions=total_sessions,
        total_messages=total_messages,
        favorite_persona=favorite_persona,
        avg_daily_messages=avg_daily_messages,
        retention_days=retention_days,
        tier=tier,
    )


def get_revenue_report(
    db: Session,
    period: str = "monthly",
) -> RevenueReport:
    """
    Generate a revenue report for the specified period.

    period:
        "daily"   → last 24 hours
        "weekly"  → last 7 days
        "monthly" → last 30 days
    """
    _period_map = {
        "daily": 1,
        "weekly": 7,
        "monthly": 30,
    }
    if period not in _period_map:
        period = "monthly"

    days = _period_map[period]
    window = _naive(_window_start(days))

    # Total revenue in period
    revenue_cents = (
        db.query(func.sum(Purchase.amount_usd))
        .filter(
            Purchase.deleted_at == None,
            Purchase.purchased_at >= window,
        )
        .scalar() or 0
    )
    total_revenue_usd = _cents_to_usd(revenue_cents)

    # New subscribers in period
    new_subscribers = (
        db.query(func.count(Subscription.id))
        .filter(
            Subscription.created_at >= window,
            Subscription.deleted_at == None,
        )
        .scalar() or 0
    )

    # Churned: subscriptions that moved to "cancelled" status in period
    churned_subscribers = (
        db.query(func.count(Subscription.id))
        .filter(
            Subscription.status == "cancelled",
            Subscription.created_at >= window,
        )
        .scalar() or 0
    )

    # MRR from currently active subscriptions
    mrr = _calculate_mrr(db)

    # ARPU: MRR / active subscriber count
    active_sub_count = (
        db.query(func.count(Subscription.id))
        .filter(
            Subscription.status == "active",
            Subscription.deleted_at == None,
        )
        .scalar() or 0
    )
    arpu = round(mrr / active_sub_count, 2) if active_sub_count > 0 else 0.0

    # Top personas by revenue in period
    top_rows = (
        db.query(
            Purchase.persona_id,
            func.count(Purchase.id).label("purchases"),
            func.sum(Purchase.amount_usd).label("revenue_cents"),
        )
        .filter(
            Purchase.deleted_at == None,
            Purchase.purchased_at >= window,
        )
        .group_by(Purchase.persona_id)
        .order_by(func.sum(Purchase.amount_usd).desc())
        .limit(10)
        .all()
    )

    top_personas = [
        {
            "persona_id": row.persona_id,
            "revenue_usd": _cents_to_usd(row.revenue_cents),
            "purchases": row.purchases,
        }
        for row in top_rows
    ]

    return RevenueReport(
        period=period,
        total_revenue_usd=total_revenue_usd,
        new_subscribers=new_subscribers,
        churned_subscribers=churned_subscribers,
        mrr=mrr,
        arpu=arpu,
        top_personas=top_personas,
    )


def get_daily_active_users(
    db: Session,
    days: int = 30,
) -> list[dict]:
    """
    Return a time-series list of daily active user counts.

    Returns:
        [{"date": "2024-06-01", "count": 42}, ...]
    Ordered from oldest to newest.
    """
    window = _naive(_window_start(days))

    # Use SQLAlchemy func to group by date.
    # Works on both SQLite (via strftime) and PostgreSQL (via DATE()).
    from sqlalchemy import text as sa_text

    db_url = str(db.bind.url) if hasattr(db, "bind") and db.bind else ""

    try:
        # Try PostgreSQL-style DATE cast
        from sqlalchemy import cast, Date as SADate
        rows = (
            db.query(
                cast(APIKeyUsage.timestamp, SADate).label("day"),
                func.count(distinct(APIKeyUsage.user_id)).label("count"),
            )
            .filter(APIKeyUsage.timestamp >= window)
            .group_by(cast(APIKeyUsage.timestamp, SADate))
            .order_by(cast(APIKeyUsage.timestamp, SADate))
            .all()
        )
    except Exception:
        # Fallback: return empty list rather than crash
        return []

    result = []
    for row in rows:
        day = row.day
        # Normalise to string
        if hasattr(day, "isoformat"):
            day_str = day.isoformat()
        else:
            day_str = str(day)
        result.append({"date": day_str, "count": row.count})

    return result


def get_cohort_retention(
    db: Session,
    cohort_month: str,
) -> dict:
    """
    Compute month-over-month retention for a signup cohort.

    cohort_month: "YYYY-MM" format, e.g. "2024-06"
    Returns:
        {
            "cohort_month": "2024-06",
            "cohort_size": 120,
            "retention": {
                "month_0": 120,   # signed up
                "month_1": 85,    # still active 1 month later
                "month_2": 62,
                ...
            },
            "retention_rates": {
                "month_0": 1.0,
                "month_1": 0.708,
                ...
            }
        }
    """
    try:
        year, month = map(int, cohort_month.split("-"))
    except (ValueError, AttributeError):
        return {
            "cohort_month": cohort_month,
            "cohort_size": 0,
            "retention": {},
            "retention_rates": {},
            "error": "Invalid cohort_month format. Use YYYY-MM.",
        }

    # Start and end of cohort month
    cohort_start = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    cohort_end   = datetime(year, month, last_day, 23, 59, 59)

    # Users who signed up in this cohort month
    cohort_users = (
        db.query(User.id)
        .filter(
            User.created_at >= cohort_start,
            User.created_at <= cohort_end,
            User.deleted_at == None,
        )
        .all()
    )
    cohort_user_ids = {u.id for u in cohort_users}
    cohort_size = len(cohort_user_ids)

    if cohort_size == 0:
        return {
            "cohort_month": cohort_month,
            "cohort_size": 0,
            "retention": {},
            "retention_rates": {},
        }

    # For each subsequent month (up to 12), count how many cohort users were active
    retention: dict[str, int] = {}
    retention_rates: dict[str, float] = {}

    now = _utc_now().replace(tzinfo=None)

    for m_offset in range(13):  # month_0 through month_12
        # Calculate the month boundaries for this offset
        target_month_num = month + m_offset
        target_year = year + (target_month_num - 1) // 12
        target_month_num = ((target_month_num - 1) % 12) + 1

        month_start = datetime(target_year, target_month_num, 1)
        if month_start > now:
            break  # Don't project into the future

        last_day_of_month = calendar.monthrange(target_year, target_month_num)[1]
        month_end = datetime(target_year, target_month_num, last_day_of_month, 23, 59, 59)

        if m_offset == 0:
            # month_0: everyone in the cohort counts as retained
            count = cohort_size
        else:
            # Count cohort members with any API usage in this month
            count = (
                db.query(func.count(distinct(APIKeyUsage.user_id)))
                .filter(
                    APIKeyUsage.user_id.in_(cohort_user_ids),
                    APIKeyUsage.timestamp >= month_start,
                    APIKeyUsage.timestamp <= month_end,
                )
                .scalar() or 0
            )

        key = f"month_{m_offset}"
        retention[key] = count
        retention_rates[key] = round(count / cohort_size, 4)

    return {
        "cohort_month": cohort_month,
        "cohort_size": cohort_size,
        "retention": retention,
        "retention_rates": retention_rates,
    }


# ── CSV export helpers ─────────────────────────────────────────────────────────

import csv
import io as _io


def export_revenue_csv(db: Session, period: str = "monthly") -> str:
    """
    Generate a CSV string for the revenue report.

    Columns: period, total_revenue_usd, new_subscribers, churned_subscribers, mrr, arpu
    Followed by a top-personas breakdown section.
    """
    report = get_revenue_report(db, period=period)
    output = _io.StringIO()
    writer = csv.writer(output)

    # Summary header
    writer.writerow([
        "period", "total_revenue_usd", "new_subscribers",
        "churned_subscribers", "mrr", "arpu",
    ])
    writer.writerow([
        report.period,
        report.total_revenue_usd,
        report.new_subscribers,
        report.churned_subscribers,
        report.mrr,
        report.arpu,
    ])

    # Top personas breakdown
    writer.writerow([])
    writer.writerow(["persona_id", "revenue_usd", "purchases"])
    for p in report.top_personas:
        writer.writerow([p["persona_id"], p["revenue_usd"], p["purchases"]])

    return output.getvalue()


def export_dau_csv(db: Session, days: int = 30) -> str:
    """Generate a CSV string for the DAU time series."""
    dau = get_daily_active_users(db, days=days)
    output = _io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "active_users"])
    for row in dau:
        writer.writerow([row["date"], row["count"]])
    return output.getvalue()


def export_top_personas_csv(db: Session, limit: int = 10, days: int = 30) -> str:
    """Generate a CSV string for the top personas report."""
    personas = get_top_personas(db, limit=limit, days=days)
    output = _io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "persona_id", "total_conversations", "total_messages",
        "unique_users", "avg_session_length", "revenue_usd",
    ])
    for p in personas:
        writer.writerow([
            p.persona_id,
            p.total_conversations,
            p.total_messages,
            p.unique_users,
            p.avg_session_length,
            p.revenue_usd,
        ])
    return output.getvalue()


# ── Analytics helpers (also exposed in db.py-compatible style) ─────────────────


def count_users(db: Session) -> int:
    """Count active (non-deleted) users."""
    return db.query(func.count(User.id)).filter(User.deleted_at == None).scalar() or 0


def count_purchases(db: Session) -> int:
    """Count total non-deleted purchases."""
    return db.query(func.count(Purchase.id)).filter(Purchase.deleted_at == None).scalar() or 0


def total_revenue_cents(db: Session) -> int:
    """Sum of all Purchase.amount_usd (stored in cents) for non-deleted purchases."""
    result = (
        db.query(func.sum(Purchase.amount_usd))
        .filter(Purchase.deleted_at == None)
        .scalar()
    )
    return result or 0
