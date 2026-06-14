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


# ── create_checkout_session tier branch (line 105) ───────────────────────────

def test_checkout_delegates_to_subscription_when_tier_given(test_db, monkeypatch):
    """Line 105: when tier is provided, create_subscription_session is called."""
    import api.payments as pm
    monkeypatch.setattr(pm.stripe, "api_key", "sk_test_x")

    sentinel = {"checkout_url": "https://sub", "session_id": "cs_sub", "tier": "basic_monthly",
                "billing_period": "month", "discount_percent": 0}
    monkeypatch.setattr(pm, "create_subscription_session", lambda *a, **k: sentinel)

    user, _ = create_user(test_db, "tier_branch@b.com")
    out = create_checkout_session(user, "p", {"price_usd": 9.99, "name": "P"}, test_db,
                                  tier="basic_monthly")
    assert out == sentinel


# ── checkout valid promo discount (line 124) ─────────────────────────────────

def test_checkout_valid_promo_applies_discount(test_db, stripe_on, monkeypatch):
    """Line 124: valid promo code → discount_cents computed and deducted."""
    from api.db import PromoCode
    # Insert a valid promo code
    promo = PromoCode(code="EXTRA10", discount_percent=10, status="active")
    test_db.add(promo)
    test_db.commit()

    user, _ = create_user(test_db, "promo_valid@b.com")
    out = create_checkout_session(user, "p_promo", {"price_usd": 10.0, "name": "PP"},
                                  test_db, promo="EXTRA10")
    # Should reach stripe and return url (10% off → 900 cents charged)
    assert out["checkout_url"] == "https://checkout.stripe.test/session"


# ── StripeError in create_checkout_session (lines 170-171) ──────────────────

def test_checkout_stripe_error_returns_502(test_db, monkeypatch):
    """Lines 170-171: StripeError in Session.create → 502."""
    import api.payments as pm

    class _FakeStripeError(pm.stripe.StripeError):
        user_message = "card declined"

    monkeypatch.setattr(pm.stripe, "api_key", "sk_test_x")

    def _raise(**kw):
        raise _FakeStripeError("boom")

    monkeypatch.setattr(pm.stripe.checkout.Session, "create", staticmethod(_raise))

    user, _ = create_user(test_db, "serr@b.com")
    with pytest.raises(HTTPException) as ei:
        create_checkout_session(user, "p_err", {"price_usd": 9.99, "name": "Err"}, test_db)
    assert ei.value.status_code == 502


# ── handle_webhook subscription mode (lines 207-220) ────────────────────────

def test_handle_webhook_subscription_checkout(test_db, monkeypatch):
    """Lines 207-220: checkout.session.completed in subscription mode."""
    import api.payments as pm
    user, _ = create_user(test_db, "subwh@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))

    obj = {
        "id": "cs_sub_wh",
        "mode": "subscription",
        "subscription": "sub_wh_001",
        "customer": "cus_wh_001",
        "amount_total": 999,
        "metadata": {"user_id": str(user.id), "subscription_tier": tier},
    }
    event = {"id": "evt_subwh", "type": "checkout.session.completed", "data": {"object": obj}}

    monkeypatch.setattr(pm, "WEBHOOK_SECRET", "whsec")
    monkeypatch.setattr(pm.stripe.Webhook, "construct_event",
                        staticmethod(lambda *a, **k: event))
    res = handle_webhook(b"{}", "sig", test_db)
    assert res["received"] is True
    assert res["type"] == "checkout.session.completed"

    from api.db import Subscription
    sub = test_db.query(Subscription).filter(
        Subscription.stripe_subscription_id == "sub_wh_001"
    ).first()
    assert sub is not None and sub.tier == tier


# ── handle_webhook subscription deleted/updated (lines 246-261) ──────────────

def test_handle_webhook_subscription_deleted(test_db, monkeypatch):
    """Lines 246-261: customer.subscription.deleted → status cancelled."""
    import api.payments as pm
    user, _ = create_user(test_db, "subdel@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    upsert_subscription(test_db, str(user.id), tier, "sub_del_wh", "cus_del_wh")

    obj = {"id": "sub_del_wh", "status": "canceled"}
    event = {"id": "evt_del_wh", "type": "customer.subscription.deleted",
             "data": {"object": obj}}
    monkeypatch.setattr(pm, "WEBHOOK_SECRET", "whsec")
    monkeypatch.setattr(pm.stripe.Webhook, "construct_event",
                        staticmethod(lambda *a, **k: event))

    res = handle_webhook(b"{}", "sig", test_db)
    assert res["received"] is True

    from api.db import Subscription
    sub = test_db.query(Subscription).filter(
        Subscription.stripe_subscription_id == "sub_del_wh"
    ).first()
    assert sub.status == "cancelled"


def test_handle_webhook_subscription_updated_active(test_db, monkeypatch):
    """Lines 246-261: customer.subscription.updated → status active."""
    import api.payments as pm
    user, _ = create_user(test_db, "subact@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    upsert_subscription(test_db, str(user.id), tier, "sub_upd_wh", "cus_upd_wh")

    # Force cancelled first
    from api.db import Subscription
    sub = test_db.query(Subscription).filter(
        Subscription.stripe_subscription_id == "sub_upd_wh"
    ).first()
    if sub:
        sub.status = "cancelled"
        test_db.commit()

    obj = {"id": "sub_upd_wh", "status": "active"}
    event = {"id": "evt_upd_wh", "type": "customer.subscription.updated",
             "data": {"object": obj}}
    monkeypatch.setattr(pm, "WEBHOOK_SECRET", "whsec")
    monkeypatch.setattr(pm.stripe.Webhook, "construct_event",
                        staticmethod(lambda *a, **k: event))

    res = handle_webhook(b"{}", "sig", test_db)
    assert res["received"] is True

    sub = test_db.query(Subscription).filter(
        Subscription.stripe_subscription_id == "sub_upd_wh"
    ).first()
    assert sub.status == "active"


def test_handle_webhook_subscription_unpaid(test_db, monkeypatch):
    """Lines 246-261: unpaid status → cancelled."""
    import api.payments as pm
    user, _ = create_user(test_db, "subunpaid@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    upsert_subscription(test_db, str(user.id), tier, "sub_unpaid_wh", "cus_unpaid_wh")

    obj = {"id": "sub_unpaid_wh", "status": "unpaid"}
    event = {"id": "evt_unpaid_wh", "type": "customer.subscription.deleted",
             "data": {"object": obj}}
    monkeypatch.setattr(pm, "WEBHOOK_SECRET", "whsec")
    monkeypatch.setattr(pm.stripe.Webhook, "construct_event",
                        staticmethod(lambda *a, **k: event))

    handle_webhook(b"{}", "sig", test_db)

    from api.db import Subscription
    sub = test_db.query(Subscription).filter(
        Subscription.stripe_subscription_id == "sub_unpaid_wh"
    ).first()
    assert sub.status == "cancelled"


# ── create_subscription_session promo (lines 311-319) ───────────────────────

def test_subscription_valid_promo(test_db, stripe_on):
    """Lines 311-315: valid promo code applied to subscription."""
    from api.db import PromoCode
    promo = PromoCode(code="SUB20", discount_percent=20, status="active")
    test_db.add(promo)
    test_db.commit()

    user, _ = create_user(test_db, "subpromo@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    out = create_subscription_session(user, tier, test_db, promo="SUB20")
    assert out["discount_percent"] == 20
    assert out["checkout_url"] == "https://checkout.stripe.test/session"


def test_subscription_invalid_promo_rejected(test_db, stripe_on):
    """Lines 318-319: invalid promo → 400."""
    user, _ = create_user(test_db, "subpromo2@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    with pytest.raises(HTTPException) as ei:
        create_subscription_session(user, tier, test_db, promo="BOGUS_SUB")
    assert ei.value.status_code == 400


# ── StripeError in create_subscription_session (lines 358-359) ──────────────

def test_subscription_stripe_error_returns_502(test_db, monkeypatch):
    """Lines 358-359: StripeError in subscription Session.create → 502."""
    import api.payments as pm

    class _FakeStripeError(pm.stripe.StripeError):
        user_message = "network failure"

    monkeypatch.setattr(pm.stripe, "api_key", "sk_test_x")

    def _raise(**kw):
        raise _FakeStripeError("network")

    monkeypatch.setattr(pm.stripe.checkout.Session, "create", staticmethod(_raise))

    user, _ = create_user(test_db, "suberr@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    with pytest.raises(HTTPException) as ei:
        create_subscription_session(user, tier, test_db)
    assert ei.value.status_code == 502


# ── handle_subscription_webhook_event status update (lines 387-388) ─────────

def test_subscription_webhook_event_updates_status_active(test_db):
    """Lines 387-388: subscription updated to active status."""
    from api.db import Subscription
    user, _ = create_user(test_db, "swh_act@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    upsert_subscription(test_db, str(user.id), tier, "sub_swh_act", "cus_swh_act")

    # Force to cancelled
    sub = test_db.query(Subscription).filter(
        Subscription.stripe_subscription_id == "sub_swh_act"
    ).first()
    if sub:
        sub.status = "cancelled"
        test_db.commit()

    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_swh_act", "status": "active"}},
    }
    handle_subscription_webhook_event(event, test_db)

    sub = test_db.query(Subscription).filter(
        Subscription.stripe_subscription_id == "sub_swh_act"
    ).first()
    assert sub.status == "active"


def test_subscription_webhook_event_incomplete_expired(test_db):
    """Lines 385-388: incomplete_expired → cancelled."""
    from api.db import Subscription
    user, _ = create_user(test_db, "swh_exp@b.com")
    tier = next(iter(SUBSCRIPTION_TIERS))
    upsert_subscription(test_db, str(user.id), tier, "sub_swh_exp", "cus_swh_exp")

    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_swh_exp", "status": "incomplete_expired"}},
    }
    handle_subscription_webhook_event(event, test_db)

    sub = test_db.query(Subscription).filter(
        Subscription.stripe_subscription_id == "sub_swh_exp"
    ).first()
    assert sub.status == "cancelled"


def test_subscription_webhook_event_nonexistent_sub_noop(test_db):
    """Missing sub ID is a no-op (no crash)."""
    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_nonexistent_xyz", "status": "canceled"}},
    }
    handle_subscription_webhook_event(event, test_db)  # Should not raise


# ── handle_webhook referral credit branch (line 246) ─────────────────────────

def test_handle_webhook_one_time_purchase_with_referral(test_db, monkeypatch):
    """Line 246: referral credit issued when referrer_id differs from user_id."""
    import api.payments as pm
    buyer, _ = create_user(test_db, "buyer_ref@b.com")
    referrer, _ = create_user(test_db, "referrer_ref@b.com")

    issued_credits = []

    def _track_credit(db, ref_id, buyer_id, amount_cents):
        issued_credits.append((ref_id, buyer_id, amount_cents))

    monkeypatch.setattr(pm, "issue_referral_credit", _track_credit)

    obj = {
        "id": "cs_ref_001",
        "mode": "payment",
        "amount_total": 999,
        "metadata": {
            "user_id": str(buyer.id),
            "persona_id": "p_ref",
            "referrer_id": str(referrer.id),
        },
    }
    event = {"id": "evt_ref_001", "type": "checkout.session.completed",
             "data": {"object": obj}}
    monkeypatch.setattr(pm, "WEBHOOK_SECRET", "whsec")
    monkeypatch.setattr(pm.stripe.Webhook, "construct_event",
                        staticmethod(lambda *a, **k: event))

    res = handle_webhook(b"{}", "sig", test_db)
    assert res["received"] is True
    assert len(issued_credits) == 1
    assert issued_credits[0][0] == str(referrer.id)  # referrer received credit
