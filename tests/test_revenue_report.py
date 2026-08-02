import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.revenue_report import build_report  # noqa: E402

import stripe


def test_revenue_report_empty(client):
    report = build_report()
    assert report["total_revenue_usd"] == 0
    assert report["paid_purchase_count"] == 0
    assert report["unique_paying_users"] == 0


def test_revenue_report_reflects_paid_purchases(client, auth_headers, monkeypatch):
    class _FakeSession:
        id = "cs_test_rev"
        url = "https://checkout.stripe.com/test"

    monkeypatch.setattr(stripe.checkout.Session, "create", lambda **kw: _FakeSession())
    r = client.post("/checkout/mandela", headers=auth_headers)
    session_id = r.json()["session_id"]

    fake_event = {"type": "checkout.session.completed", "data": {"object": {"id": session_id}}}
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda *a, **kw: fake_event)
    client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "sig"})

    report = build_report()
    assert report["paid_purchase_count"] == 1
    assert report["revenue_by_persona"]["mandela"] == 9.99
    assert report["unique_paying_users"] == 1
