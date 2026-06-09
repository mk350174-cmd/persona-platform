"""
Stripe payment integration.

Environment variables required:
  STRIPE_SECRET_KEY      sk_live_... or sk_test_...
  STRIPE_WEBHOOK_SECRET  whsec_...
  BASE_URL               https://yourdomain.com  (for redirect URLs)

Flow:
  1. POST /checkout/{persona_id}  → returns {checkout_url}
  2. User pays on Stripe hosted page
  3. Stripe POST /webhook/stripe  → records purchase in DB
  4. User can now call /v1/compile/{persona_id}
"""

import os

import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.db import (
    User, record_purchase, has_purchased, upsert_subscription, SUBSCRIPTION_TIERS, is_stripe_event_processed, mark_stripe_event_processed,
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _price_cents(price_usd: float) -> int:
    return int(round(price_usd * 100))


def create_checkout_session(
    user: User,
    persona_id: str,
    persona_meta: dict,
    db: Session,
) -> dict:
    """
    Create a Stripe Checkout Session for a persona purchase.

    Returns
    -------
    dict with 'checkout_url' and 'session_id'
    """
    if not stripe.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system not configured. Set STRIPE_SECRET_KEY.",
        )

    price_usd = persona_meta.get("price_usd", 0)
    if price_usd == 0:
        raise HTTPException(status_code=400, detail="This persona is free — no checkout needed.")

    if has_purchased(db, user.id, persona_id):
        raise HTTPException(status_code=400, detail="Already purchased.")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": _price_cents(price_usd),
                    "product_data": {
                        "name": persona_meta["name"],
                        "description": persona_meta.get("tagline", ""),
                        "metadata": {"persona_id": persona_id},
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{BASE_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/checkout/cancel",
            metadata={
                "user_id": user.id,
                "persona_id": persona_id,
            },
            customer_email=user.email,
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message}")


def handle_webhook(raw_body: bytes, stripe_signature: str, db: Session) -> dict:
    """
    Verify and process a Stripe webhook event.

    Handles: checkout.session.completed → record purchase
    """
    if not WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret not configured. Set STRIPE_WEBHOOK_SECRET.",
        )

    try:
        event = stripe.Webhook.construct_event(raw_body, stripe_signature, WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    event_id = event["id"]
    event_type = event["type"]

    if is_stripe_event_processed(db, event_id):
        return {"received": True, "type": event_type, "duplicate": True}

    obj = event["data"]["object"]
    mode = obj.get("mode")

    if event_type == "checkout.session.completed":
        meta = obj.get("metadata", {})
        user_id = meta.get("user_id")

        if mode == "subscription":
            # Recurring subscription purchase
            tier = meta.get("subscription_tier")
            stripe_sub_id = obj.get("subscription")
            stripe_customer_id = obj.get("customer")
            if user_id and tier:
                upsert_subscription(db, user_id, tier, stripe_sub_id, stripe_customer_id)
        else:
            # One-time persona purchase
            persona_id = meta.get("persona_id")
            amount_cents = obj.get("amount_total")
            if user_id and persona_id:
                if not has_purchased(db, user_id, persona_id):
                    record_purchase(
                        db,
                        user_id=user_id,
                        persona_id=persona_id,
                        stripe_session_id=obj["id"],
                        amount_cents=amount_cents,
                    )

    elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        stripe_sub_id = obj.get("id")
        new_status = obj.get("status")
        if stripe_sub_id:
            from api.db import Subscription
            sub = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == stripe_sub_id
            ).first()
            if sub:
                if new_status in ("canceled", "unpaid", "incomplete_expired"):
                    sub.status = "cancelled"
                elif new_status == "active":
                    sub.status = "active"
                db.commit()

    mark_stripe_event_processed(db, event_id, event_type)
    return {"received": True, "type": event_type}


def create_subscription_session(user: User, tier: str, db: Session) -> dict:
    """
    Create a Stripe Checkout Session for a monthly subscription.

    Returns {checkout_url, session_id}
    """
    if not stripe.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system not configured. Set STRIPE_SECRET_KEY.",
        )

    tier_cfg = SUBSCRIPTION_TIERS.get(tier)
    if not tier_cfg:
        raise HTTPException(status_code=400, detail=f"Unknown tier '{tier}'. Choose: {list(SUBSCRIPTION_TIERS.keys())}")

    price_cents = _price_cents(tier_cfg["price_usd"])

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "recurring": {"interval": "month"},
                    "unit_amount": price_cents,
                    "product_data": {
                        "name": f"Persona Hub — {tier_cfg['label']}",
                        "description": (
                            f"{tier_cfg['monthly_requests'] or 'Unlimited'} API calls/month"
                        ),
                    },
                },
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{BASE_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL}/checkout/cancel",
            metadata={
                "user_id": user.id,
                "subscription_tier": tier,
            },
            customer_email=user.email,
        )
        return {"checkout_url": session.url, "session_id": session.id, "tier": tier}
    except stripe.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message}")


def handle_subscription_webhook_event(event: dict, db: Session) -> None:
    """Process Stripe subscription lifecycle events."""
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed" and obj.get("mode") == "subscription":
        meta = obj.get("metadata", {})
        user_id = meta.get("user_id")
        tier = meta.get("subscription_tier")
        stripe_sub_id = obj.get("subscription")
        stripe_customer_id = obj.get("customer")
        if user_id and tier:
            upsert_subscription(db, user_id, tier, stripe_sub_id, stripe_customer_id)

    elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        stripe_sub_id = obj.get("id")
        new_status = obj.get("status")
        if stripe_sub_id:
            from api.db import Subscription
            sub = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == stripe_sub_id
            ).first()
            if sub:
                if new_status in ("canceled", "unpaid", "incomplete_expired"):
                    sub.status = "cancelled"
                elif new_status == "active":
                    sub.status = "active"
                db.commit()


def mock_purchase(user: User, persona_id: str, db: Session) -> dict:
    """
    Development-only: grant persona access without Stripe.
    Disabled in production (STRIPE_SECRET_KEY set).
    """
    is_production = os.getenv("STRIPE_SECRET_KEY", "").startswith("sk_live_")
    if is_production:
        raise HTTPException(
            status_code=403,
            detail="Mock purchases disabled in production.",
        )
    if has_purchased(db, user.id, persona_id):
        return {"status": "already_owned", "persona_id": persona_id}

    record_purchase(db, user_id=user.id, persona_id=persona_id, stripe_session_id="mock")
    return {"status": "granted", "persona_id": persona_id, "mode": "development_mock"}
