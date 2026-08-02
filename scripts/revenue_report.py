"""Revenue analytics skeleton (T2-027). A script, not an API endpoint --
this repo has no RBAC/admin role yet (T2-009 only has a single user role),
so exposing aggregate revenue over HTTP to any authenticated user would be
a real data leak. Run this directly against the database instead.

Honesty note: "MRR"/"ARPU"/"churn" are subscription-model metrics. The
only monetization model actually implemented (T2-021/026) is one-time
per-persona purchases (T2-024 left the subscription/credit question as
deferred-decision) -- so this reports what that model actually supports:
total revenue, revenue by persona, and paying-user count. It does NOT
compute MRR/churn, since there is no recurring-billing data to compute
them from; adding those metrics before a subscription model exists would
mean reporting invented numbers.

Usage:
    python3 scripts/revenue_report.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.db import SessionLocal, Purchase  # noqa: E402


def build_report() -> dict:
    db = SessionLocal()
    try:
        paid = db.query(Purchase).filter(Purchase.stripe_payment_status == "paid").all()
        pending = db.query(Purchase).filter(Purchase.stripe_payment_status == "pending").count()

        # Price is a code constant (payments_router.PERSONA_PRICE_USD_CENTS),
        # not stored per-purchase -- fine while there's one flat price, but
        # a genuine per-purchase amount column would be needed the day
        # pricing varies by persona or changes over time.
        from api.routers.payments_router import PERSONA_PRICE_USD_CENTS

        by_persona: dict[str, int] = defaultdict(int)
        paying_users = set()
        for p in paid:
            by_persona[p.persona_id] += 1
            paying_users.add(p.user_id)

        total_cents = len(paid) * PERSONA_PRICE_USD_CENTS

        return {
            "total_revenue_usd": round(total_cents / 100, 2),
            "paid_purchase_count": len(paid),
            "pending_purchase_count": pending,
            "unique_paying_users": len(paying_users),
            "revenue_by_persona": {
                pid: round(count * PERSONA_PRICE_USD_CENTS / 100, 2)
                for pid, count in by_persona.items()
            },
            "note": (
                "One-time per-persona purchases only. MRR/ARPU/churn are "
                "subscription metrics and don't apply to this model "
                "(T2-024 deferred-decision) -- not computed here."
            ),
        }
    finally:
        db.close()


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2))
