"""
Extra unit tests for api/payments.py — pricing, checkout, webhooks, mock purchase.

Stripe is never really called: `payments.stripe` API surfaces are monkeypatched.
DB-backed paths use the `test_db` fixture and real `api.db` helpers.
"""

import pytest
from fastapi import HTTPException

import api.payments as payments
from api.payments import (
    _price_cents,
    locale_to_currency,
    get_localized_price,
    create_checkout_session,
    create_subscription_session,
    handle_webhook,
    handle_subscription_webhook_event,
    mock_purchase,
)
from api.db import (
    create_user, has_purchased, get_or_create_wallet, add_wallet_credit,
    upsert_subscription, SUBSCRIPTION_TIERS,
)


# ── pure pricing ─────────────────────────────────────────────────────────────

def test_price_cents_rounding():
    assert _price_cents(9.99) == 999
    assert _price_cents(0.1) == 10


def test_locale_to_currency():
    assert locale_to_currency("eur") == "eur"
    assert locale_to_currency("TRY") == "try"
    assert locale_to_currency("unknown") == "usd"


def test_get_localized_price():
    assert get_localized_price(10.0, "usd") == 10.0
    assert get_localized_price(10.0, "eur") == pytest.approx(9.2)
    assert get_localized_price(10.0, "xyz") == 10.0   # unknown → 1.0 rate


# ── fake stripe session ──────────────────────────────────────────────────────

class _FakeSession:
    url = "https://checkout.stripe.test/session"
    id = "cs_test_123"


@pytest.fixture
def stripe_on(monkeypatch):
    """Enable a fake Stripe: api_key set, Session.create returns a stub."""
    monkeypatch.setattr(payments.stripe, "api_key", "sk_test_x")
    monkeypatch.setattr(payments.stripe.checkout.Session, "create",
                        staticmethod(lambda **kw: _FakeSession()))
    return _FakeSession


# ── create_checkout_session ──────────────────────────────────────────────────

def test_checkout_requires_stripe_key(test_db, monkeypatch):
    monkeypatch.setattr(payments.stripe, "api_key", "")
    user, _ = create_user(test_db, "a@b.com")
    with pytest.raises(HTTPException) as ei:
        create_checkout_session(user, "p", {"price_usd": 5}, test_db)
    assert ei.value.status_code == 503


def test_checkout_free_persona_rejected(test_db, stripe_on):
    user, _ = create_user(test_db, "free@b.com")
    with pytest.raises(HTTPException) as ei:
        create_checkout_session(user, "p", {"price_usd": 0}, test_db)
    assert ei.value.status_code == 400


def test_checkout_already_purchased(test_db, stripe_on):
    from api.db import record_purchase
    user, _ = create_user(test_db, "owner@b.com")
    record_purchase(test_db, user_id=user.id, persona_id="p", amount_cents=999)
    with pytest.raises(HTTPException) as ei:
        create_checkout_session(user, "p", {"price_usd": 9.99, "name": "P"}, test_db)
    assert ei.value.status_code == 400


def test_checkout_wallet_fully_covers_is_free_grant(test_db, stripe_on):
    user, _ = create_user(test_db, "wallet@b.com")
    get_or_create_wallet(test_db, user.id)
    add_wallet_credit(test_db, user.id, 100_000)   # plenty
    out = create_checkout_session(user, "p", {"price_usd": 9.99, "name": "P"}, test_db)
    assert out["status"] == "free_grant"
    assert has_purchased(test_db, user.id, "p")


def test_checkout_card_charge_returns_url(test_db, stripe_on):
    user, _ = create_user(test_db, "buyer@b.com")
    out = create_checkout_session(user, "p", {"price_usd": 9.99, "name": "Plato",
                                              "tagline": "philosopher"}, test_db)
    assert out["checkout_url"] == "https://checkout.stripe.test/session"
    assert out["session_id"] == "cs_test_123"


def test_checkout_invalid_promo_rejected(test_db, stripe_on):
    user, _ = create_user(test_db, "promo@b.com")
    with pytest.raises(HTTPException) as ei:
        create_checkout_session(user, "p", {"price_usd": 9.99, "name": "P"}, test_db,
                                promo="NOPE")
    assert ei.value.status_code == 400


# ── create_subscription_session ──────────────────────────────────────────────

def test_subscription_unknown_tier(test_db, stripe_on):
    user, _ = create_user(test_db, "sub@b.com")
    with pytest.raises(HTTPException) as ei:
        create_subscription_session(user, "ghost_tier", test_db)
    assert ei.value.status_code == 400


def test_subscription_success(test_db, stripe_on):
    user, _ = create_user(test_db, "sub2@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    out = create_subscription_session(user, tier, test_db)
    assert out["tier"] == tier
    assert out["checkout_url"] == "https://checkout.stripe.test/session"


def test_subscription_requires_key(test_db, monkeypatch):
    monkeypatch.setattr(payments.stripe, "api_key", "")
    user, _ = create_user(test_db, "sub3@b.com")
    with pytest.raises(HTTPException) as ei:
        create_subscription_session(user, next(iter(SUBSCRIPTION_TIERS)), test_db)
    assert ei.value.status_code == 503


# ── handle_webhook ───────────────────────────────────────────────────────────

def _event(event_type, obj, event_id="evt_1"):
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


def test_handle_webhook_requires_secret(test_db, monkeypatch):
    monkeypatch.setattr(payments, "WEBHOOK_SECRET", "")
    with pytest.raises(HTTPException) as ei:
        handle_webhook(b"{}", "sig", test_db)
    assert ei.value.status_code == 503


def test_handle_webhook_one_time_purchase(test_db, monkeypatch):
    user, _ = create_user(test_db, "wh@b.com")
    monkeypatch.setattr(payments, "WEBHOOK_SECRET", "whsec")
    event = _event("checkout.session.completed", {
        "id": "cs_1", "mode": "payment", "amount_total": 999,
        "metadata": {"user_id": user.id, "persona_id": "socrates"},
    })
    monkeypatch.setattr(payments.stripe.Webhook, "construct_event",
                        staticmethod(lambda *a, **k: event))
    res = handle_webhook(b"{}", "sig", test_db)
    assert res["received"] is True
    assert has_purchased(test_db, user.id, "socrates")


def test_handle_webhook_duplicate(test_db, monkeypatch):
    user, _ = create_user(test_db, "dup@b.com")
    monkeypatch.setattr(payments, "WEBHOOK_SECRET", "whsec")
    event = _event("checkout.session.completed", {
        "id": "cs_2", "mode": "payment", "amount_total": 999,
        "metadata": {"user_id": user.id, "persona_id": "x"},
    }, event_id="evt_dup")
    monkeypatch.setattr(payments.stripe.Webhook, "construct_event",
                        staticmethod(lambda *a, **k: event))
    handle_webhook(b"{}", "sig", test_db)
    res2 = handle_webhook(b"{}", "sig", test_db)
    assert res2.get("duplicate") is True


def test_handle_webhook_bad_signature(test_db, monkeypatch):
    monkeypatch.setattr(payments, "WEBHOOK_SECRET", "whsec")

    def _raise(*a, **k):
        raise payments.stripe.SignatureVerificationError("bad", "sig")
    monkeypatch.setattr(payments.stripe.Webhook, "construct_event", staticmethod(_raise))
    with pytest.raises(HTTPException) as ei:
        handle_webhook(b"{}", "sig", test_db)
    assert ei.value.status_code == 400


# ── handle_subscription_webhook_event ────────────────────────────────────────

def test_subscription_webhook_completed_upserts(test_db):
    user, _ = create_user(test_db, "swh@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    event = _event("checkout.session.completed", {
        "mode": "subscription", "subscription": "sub_1", "customer": "cus_1",
        "metadata": {"user_id": user.id, "subscription_tier": tier},
    })
    handle_subscription_webhook_event(event, test_db)
    from api.db import Subscription
    sub = test_db.query(Subscription).filter(Subscription.stripe_subscription_id == "sub_1").first()
    assert sub is not None and sub.tier == tier


def test_subscription_webhook_deleted_cancels(test_db):
    user, _ = create_user(test_db, "cancel@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    upsert_subscription(test_db, user.id, tier, "sub_del", "cus_del")
    event = _event("customer.subscription.deleted", {"id": "sub_del", "status": "canceled"})
    handle_subscription_webhook_event(event, test_db)
    from api.db import Subscription
    sub = test_db.query(Subscription).filter(Subscription.stripe_subscription_id == "sub_del").first()
    assert sub.status == "cancelled"


# ── mock_purchase ────────────────────────────────────────────────────────────

def test_mock_purchase_blocked_in_production(test_db, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_real")
    user, _ = create_user(test_db, "prod@b.com")
    with pytest.raises(HTTPException) as ei:
        mock_purchase(user, "p", test_db)
    assert ei.value.status_code == 403


def test_mock_purchase_grants(test_db, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    user, _ = create_user(test_db, "dev@b.com")
    res = mock_purchase(user, "socrates", test_db)
    assert res["status"] == "granted"
    assert has_purchased(test_db, user.id, "socrates")


def test_mock_purchase_already_owned(test_db, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    user, _ = create_user(test_db, "own2@b.com")
    mock_purchase(user, "p", test_db)
    res = mock_purchase(user, "p", test_db)
    assert res["status"] == "already_owned"
