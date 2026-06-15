"""
Unit tests for api/analytics.py — KPI aggregation, revenue, engagement, CSV export.

Seeds a small graph (users, purchases, usage logs, subscriptions) into `test_db`
and asserts the aggregates. Pure helpers and CSV builders are checked directly.
"""

from datetime import datetime, timezone, timedelta

import pytest

import api.analytics as analytics
from api.analytics import (
    _utc_now, _window_start, _naive, _cents_to_usd, _calculate_mrr,
    get_dashboard_summary, get_persona_usage_stats, get_top_personas,
    get_user_engagement, get_revenue_report, get_daily_active_users,
    get_cohort_retention, export_revenue_csv, export_dau_csv,
    export_top_personas_csv, count_users, count_purchases, total_revenue_cents,
)
from api.db import (
    create_user, record_purchase, upsert_subscription, APIKeyUsage,
    SUBSCRIPTION_TIERS,
)


_TIER = next(iter(SUBSCRIPTION_TIERS))


def _log_usage(db, user_id, persona_id, when=None, n=1, endpoint="/v1/chat"):
    for _ in range(n):
        db.add(APIKeyUsage(
            user_id=user_id, endpoint=endpoint, persona_id=persona_id,
            timestamp=when or datetime.now(timezone.utc),
        ))
    db.commit()


# ── pure helpers ─────────────────────────────────────────────────────────────

def test_pure_helpers():
    assert _utc_now().tzinfo is not None
    assert _window_start(7) < _utc_now()
    assert _naive(_utc_now()).tzinfo is None
    assert _naive(datetime(2020, 1, 1)).tzinfo is None    # already naive
    assert _cents_to_usd(None) == 0.0
    assert _cents_to_usd(999) == 9.99


# ── MRR ──────────────────────────────────────────────────────────────────────

def test_calculate_mrr_empty(test_db):
    assert _calculate_mrr(test_db) == 0.0


def test_calculate_mrr_with_active_sub(test_db):
    user, _ = create_user(test_db, "mrr@b.com")
    upsert_subscription(test_db, user.id, _TIER, "sub_1", "cus_1")
    assert _calculate_mrr(test_db) >= 0.0   # numeric, no crash


# ── dashboard summary ────────────────────────────────────────────────────────

def test_dashboard_summary_empty(test_db):
    s = get_dashboard_summary(test_db)
    assert s.total_users == 0
    assert s.total_purchases == 0
    assert s.total_revenue_usd == 0.0
    assert s.top_personas == []


def test_dashboard_summary_seeded(test_db):
    u1, _ = create_user(test_db, "d1@b.com")
    u2, _ = create_user(test_db, "d2@b.com")
    record_purchase(test_db, user_id=u1.id, persona_id="socrates", amount_cents=999)
    record_purchase(test_db, user_id=u2.id, persona_id="socrates", amount_cents=999)
    record_purchase(test_db, user_id=u1.id, persona_id="plato", amount_cents=500)
    _log_usage(test_db, u1.id, "socrates", n=3)
    s = get_dashboard_summary(test_db)
    assert s.total_users == 2
    assert s.total_purchases == 3
    assert s.total_revenue_usd == pytest.approx(24.98)
    assert s.top_personas[0]["persona_id"] == "socrates"
    assert s.top_personas[0]["purchases"] == 2


# ── persona usage stats ──────────────────────────────────────────────────────

def test_persona_usage_stats(test_db):
    u, _ = create_user(test_db, "pu@b.com")
    record_purchase(test_db, user_id=u.id, persona_id="socrates", amount_cents=999)
    _log_usage(test_db, u.id, "socrates", n=4)
    stats = get_persona_usage_stats(test_db, "socrates", days=30)
    assert stats.persona_id == "socrates"
    assert stats.total_messages == 4
    assert stats.unique_users == 1
    assert stats.avg_session_length == 4.0
    assert stats.revenue_usd == 9.99


def test_persona_usage_stats_no_data(test_db):
    stats = get_persona_usage_stats(test_db, "ghost", days=30)
    assert stats.total_messages == 0
    assert stats.avg_session_length == 0.0


# ── top personas (usage + purchase fallback) ─────────────────────────────────

def test_top_personas_usage_path(test_db):
    u, _ = create_user(test_db, "tp@b.com")
    _log_usage(test_db, u.id, "socrates", n=5)
    _log_usage(test_db, u.id, "plato", n=2)
    record_purchase(test_db, user_id=u.id, persona_id="socrates", amount_cents=999)
    top = get_top_personas(test_db, limit=10, days=30)
    assert top[0].persona_id == "socrates"
    assert top[0].total_messages == 5


def test_top_personas_purchase_fallback(test_db):
    # no usage logs → falls back to purchases
    u, _ = create_user(test_db, "tpf@b.com")
    record_purchase(test_db, user_id=u.id, persona_id="kant", amount_cents=2400)
    top = get_top_personas(test_db, limit=10, days=30)
    assert any(p.persona_id == "kant" for p in top)


def test_top_personas_empty(test_db):
    assert get_top_personas(test_db) == []


# ── user engagement ──────────────────────────────────────────────────────────

def test_user_engagement(test_db):
    u, _ = create_user(test_db, "ue@b.com")
    old = datetime.now(timezone.utc) - timedelta(days=5)
    _log_usage(test_db, u.id, "socrates", when=old, n=2)
    _log_usage(test_db, u.id, "socrates", n=3)
    _log_usage(test_db, u.id, "plato", n=1)
    eng = get_user_engagement(test_db, u.id)
    assert eng.user_id == u.id
    assert eng.total_messages == 6
    assert eng.favorite_persona == "socrates"
    assert eng.tier == "free"
    assert eng.retention_days >= 0


def test_user_engagement_with_subscription(test_db):
    u, _ = create_user(test_db, "ues@b.com")
    upsert_subscription(test_db, u.id, _TIER, "sub_ue", "cus_ue")
    _log_usage(test_db, u.id, "socrates", n=1)
    assert get_user_engagement(test_db, u.id).tier == _TIER


def test_user_engagement_no_activity(test_db):
    u, _ = create_user(test_db, "uena@b.com")
    eng = get_user_engagement(test_db, u.id)
    assert eng.total_messages == 0
    assert eng.favorite_persona == ""
    assert eng.retention_days == 0


# ── revenue report ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("period", ["daily", "weekly", "monthly", "bogus"])
def test_revenue_report_periods(test_db, period):
    u, _ = create_user(test_db, f"rr_{period}@b.com")
    record_purchase(test_db, user_id=u.id, persona_id="socrates", amount_cents=999)
    report = get_revenue_report(test_db, period=period)
    # bogus period normalises to monthly
    assert report.period in ("daily", "weekly", "monthly")
    assert report.total_revenue_usd >= 0.0


def test_revenue_report_with_subscriptions(test_db):
    u, _ = create_user(test_db, "rrs@b.com")
    upsert_subscription(test_db, u.id, _TIER, "sub_rr", "cus_rr")
    report = get_revenue_report(test_db, period="monthly")
    assert report.new_subscribers >= 1
    assert report.arpu >= 0.0


# ── DAU + cohort ─────────────────────────────────────────────────────────────

def test_daily_active_users(test_db):
    u, _ = create_user(test_db, "dau@b.com")
    _log_usage(test_db, u.id, "socrates", n=2)
    dau = get_daily_active_users(test_db, days=30)
    assert isinstance(dau, list)
    if dau:
        assert "date" in dau[0] and "count" in dau[0]


def test_cohort_retention_invalid_format(test_db):
    out = get_cohort_retention(test_db, "not-a-month")
    assert out["cohort_size"] == 0
    assert "error" in out


def test_cohort_retention_empty(test_db):
    out = get_cohort_retention(test_db, "2099-01")
    assert out["cohort_size"] == 0
    assert out["retention"] == {}


def test_cohort_retention_with_users(test_db):
    u, _ = create_user(test_db, "coh@b.com")
    # force created_at into a known past month
    u.created_at = datetime(2026, 1, 15)
    test_db.commit()
    out = get_cohort_retention(test_db, "2026-01")
    assert out["cohort_size"] == 1
    assert out["retention"]["month_0"] == 1
    assert out["retention_rates"]["month_0"] == 1.0


# ── CSV exports ──────────────────────────────────────────────────────────────

def test_export_revenue_csv(test_db):
    u, _ = create_user(test_db, "csv1@b.com")
    record_purchase(test_db, user_id=u.id, persona_id="socrates", amount_cents=999)
    csv_str = export_revenue_csv(test_db, period="monthly")
    assert "total_revenue_usd" in csv_str
    assert "persona_id" in csv_str


def test_export_dau_csv(test_db):
    u, _ = create_user(test_db, "csv2@b.com")
    _log_usage(test_db, u.id, "socrates", n=1)
    csv_str = export_dau_csv(test_db, days=30)
    assert "date,active_users" in csv_str


def test_export_top_personas_csv(test_db):
    u, _ = create_user(test_db, "csv3@b.com")
    _log_usage(test_db, u.id, "socrates", n=2)
    csv_str = export_top_personas_csv(test_db, limit=5, days=30)
    assert "persona_id" in csv_str and "revenue_usd" in csv_str


# ── count helpers ────────────────────────────────────────────────────────────

def test_count_helpers(test_db):
    assert count_users(test_db) == 0
    assert count_purchases(test_db) == 0
    assert total_revenue_cents(test_db) == 0
    u, _ = create_user(test_db, "ch@b.com")
    record_purchase(test_db, user_id=u.id, persona_id="socrates", amount_cents=999)
    assert count_users(test_db) == 1
    assert count_purchases(test_db) == 1
    assert total_revenue_cents(test_db) == 999
