"""Payments router tests. Stripe calls are mocked — this repo has no real
Stripe test-mode credentials, so these verify our routing/guard logic, not
Stripe's own behavior (T2-021/T2-022/T2-023)."""
from __future__ import annotations

import json

import pytest
import stripe

from api.routers import payments_router


class _FakeSession:
    id = "cs_test_123"
    url = "https://checkout.stripe.com/test-session"


def test_checkout_requires_auth(client):
    r = client.post("/checkout/mandela")
    assert r.status_code == 401


def test_checkout_unknown_persona_404s(client, auth_headers, monkeypatch):
    monkeypatch.setattr(stripe.checkout.Session, "create", lambda **kw: _FakeSession())
    r = client.post("/checkout/nobody", headers=auth_headers)
    assert r.status_code == 404


def test_checkout_creates_session(client, auth_headers, monkeypatch):
    captured = {}

    def _fake_create(**kwargs):
        captured.update(kwargs)
        return _FakeSession()

    monkeypatch.setattr(stripe.checkout.Session, "create", _fake_create)
    r = client.post("/checkout/mandela", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == "cs_test_123"
    assert body["test_mode"] is True
    assert captured["metadata"]["persona_id"] == "mandela"


def test_checkout_refuses_live_key_without_explicit_opt_in(monkeypatch):
    monkeypatch.setattr(payments_router, "STRIPE_SECRET_KEY", "sk_live_realkey")
    monkeypatch.delenv("STRIPE_ALLOW_LIVE", raising=False)
    with pytest.raises(Exception):
        payments_router._guard_live_key()


def test_webhook_rejects_bad_signature(client):
    r = client.post(
        "/webhooks/stripe",
        content=b'{"type": "checkout.session.completed"}',
        headers={"stripe-signature": "bad-sig"},
    )
    assert r.status_code == 400


def test_webhook_marks_purchase_paid(client, auth_headers, monkeypatch):
    monkeypatch.setattr(stripe.checkout.Session, "create", lambda **kw: _FakeSession())
    r = client.post("/checkout/mandela", headers=auth_headers)
    session_id = r.json()["session_id"]

    fake_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": session_id}},
    }
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda *a, **kw: fake_event)

    r = client.post(
        "/webhooks/stripe",
        content=json.dumps(fake_event).encode(),
        headers={"stripe-signature": "sig"},
    )
    assert r.status_code == 200
    assert r.json()["received"] is True


def test_list_purchases_requires_auth(client):
    r = client.get("/purchases")
    assert r.status_code == 401


def test_list_purchases_empty_by_default(client, auth_headers):
    r = client.get("/purchases", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_list_purchases_reflects_checkout(client, auth_headers, monkeypatch):
    monkeypatch.setattr(stripe.checkout.Session, "create", lambda **kw: _FakeSession())
    client.post("/checkout/mandela", headers=auth_headers)
    r = client.get("/purchases", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["persona_id"] == "mandela"
    assert body[0]["stripe_payment_status"] == "pending"
