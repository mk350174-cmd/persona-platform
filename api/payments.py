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
    get_promo_code, apply_promo_code, deduct_wallet_credit, get_or_create_wallet,
    issue_referral_credit, record_invoice,
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _price_cents(price_usd: float) -> int:
    return int(round(price_usd * 100))


# ── Multi-currency support (B23) ──────────────────────────────────────────────

def locale_to_currency(locale: str) -> str:
    """Convert locale code to Stripe currency code."""
    locale_map = {
        "usd": "usd",
        "eur": "eur",
        "try": "try",  # Turkish Lira
        "gbp": "gbp",
        "jpy": "jpy",
        "aud": "aud",
        "cad": "cad",
    }
    return locale_map.get(locale.lower(), "usd")


def get_localized_price(price_usd: float, locale: str) -> float:
    """Get localized price based on currency (simplified: use fixed exchange rates)."""
    exchange_rates = {
        "usd": 1.0,
        "eur": 0.92,     # 1 USD = 0.92 EUR
        "try": 32.5,     # 1 USD = 32.5 TRY
        "gbp": 0.79,     # 1 USD = 0.79 GBP
        "jpy": 149.5,    # 1 USD = 149.5 JPY
        "aud": 1.52,     # 1 USD = 1.52 AUD
        "cad": 1.37,     # 1 USD = 1.37 CAD
    }
    rate = exchange_rates.get(locale.lower(), 1.0)
    return price_usd * rate


def create_checkout_session(
    user: User,
    persona_id: str,
    persona_meta: dict,
    db: Session,
    tier: str | None = None,
    promo: str | None = None,
    referrer_id: str | None = None,
    locale: str = "usd",
) -> dict:
    """
    Create a Stripe Checkout Session for a persona purchase or subscription.

    Parameters
    ----------
    tier : str, optional
        Subscription tier (basic_monthly, basic_annual, pro_monthly, pro_annual).
        If provided, creates a subscription checkout instead of one-time purchase.
    promo : str, optional
        Promo code for discount (B14). Applies to both persona and subscription checkouts.
    referrer_id : str, optional
        User ID of the referrer (B21). Used to issue referral credit on purchase.
    locale : str, default "usd"
        Currency locale for pricing (B23): usd, eur, try, gbp, jpy, aud, cad

    Returns
    -------
    dict with 'checkout_url' and 'session_id'
    """
    if not stripe.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system not configured. Set STRIPE_SECRET_KEY.",
        )

    # Handle subscription tier checkout (B13)
    if tier:
        return create_subscription_session(user, tier, db, promo=promo, referrer_id=referrer_id, locale=locale)

    # One-time persona purchase
    price_usd = persona_meta.get("price_usd", 0)
    if price_usd == 0:
        raise HTTPException(status_code=400, detail="This persona is free — no checkout needed.")

    if has_purchased(db, user.id, persona_id):
        raise HTTPException(status_code=400, detail="Already purchased.")

    # B23: Get localized price and currency
    currency = locale_to_currency(locale)
    localized_price = get_localized_price(price_usd, locale)

    # B14: Apply promo code if provided
    discount_cents = 0
    if promo:
        promo_code = apply_promo_code(db, promo)
        if promo_code:
            discount_cents = int(localized_price * 100 * promo_code.discount_percent / 100)
        else:
            raise HTTPException(status_code=400, detail="Invalid or expired promo code.")

    # B22: Deduct from wallet first (always in USD cents)
    price_cents = _price_cents(localized_price) - discount_cents
    wallet = get_or_create_wallet(db, user.id)
    wallet_deduction = min(wallet.balance_cents or 0, price_cents)
    charge_cents = price_cents - wallet_deduction

    if wallet_deduction > 0:
        deduct_wallet_credit(db, user.id, wallet_deduction)

    # If fully covered by wallet, process as free purchase
    if charge_cents <= 0:
        record_purchase(db, user_id=user.id, persona_id=persona_id, amount_cents=price_cents)
        return {"checkout_url": None, "status": "free_grant", "message": "Purchased with wallet credit."}

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "unit_amount": charge_cents,
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
                "original_price_cents": _price_cents(price_usd),
                "discount_cents": discount_cents,
                "referrer_id": referrer_id or "",  # B21: referrer for credit issuance
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
        amount_cents = obj.get("amount_total", 0)

        if mode == "subscription":
            # Recurring subscription purchase (B13 annual support)
            tier = meta.get("subscription_tier")
            stripe_sub_id = obj.get("subscription")
            stripe_customer_id = obj.get("customer")
            billing_period = meta.get("billing_period", "month")
            if user_id and tier:
                upsert_subscription(db, user_id, tier, stripe_sub_id, stripe_customer_id)
                # Update stripe_customer_id on User (B13 multi-currency support)
                from api.db import User as UserModel
                user = db.query(UserModel).filter(UserModel.id == user_id).first()
                if user:
                    user.stripe_customer_id = stripe_customer_id
                    db.commit()
                # B17: Record invoice for subscription
                if stripe_sub_id:
                    record_invoice(
                        db,
                        user_id=user_id,
                        stripe_invoice_id=f"{stripe_sub_id}:{obj['id']}",
                        amount_usd_cents=amount_cents,
                        status="paid",
                        issued_at=None,  # Use current time
                        pdf_url=obj.get("invoice"),  # Stripe invoice URL
                    )
        else:
            # One-time persona purchase
            persona_id = meta.get("persona_id")
            if user_id and persona_id:
                if not has_purchased(db, user_id, persona_id):
                    record_purchase(
                        db,
                        user_id=user_id,
                        persona_id=persona_id,
                        stripe_session_id=obj["id"],
                        amount_cents=amount_cents,
                    )
                    # B21: Issue referral credit if referrer_id is in request context
                    # (This is passed from the checkout endpoint)
                    # For now, we store the referrer_id in metadata if available
                    referrer_id = meta.get("referrer_id")
                    if referrer_id and referrer_id != user_id:
                        issue_referral_credit(db, referrer_id, user_id, amount_cents=500)  # $5 default

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


def create_subscription_session(
    user: User,
    tier: str,
    db: Session,
    promo: str | None = None,
    referrer_id: str | None = None,
    locale: str = "usd",
) -> dict:
    """
    Create a Stripe Checkout Session for a subscription (monthly or annual — B13).

    Parameters
    ----------
    tier : str
        Subscription tier: basic_monthly, basic_annual, pro_monthly, pro_annual
    promo : str, optional
        Promo code for discount (B14).
    referrer_id : str, optional
        User ID of the referrer (B21). Used to issue referral credit on purchase.
    locale : str, default "usd"
        Currency locale for pricing (B23): usd, eur, try, gbp, jpy, aud, cad

    Returns {checkout_url, session_id, tier, discount_percent}
    """
    if not stripe.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system not configured. Set STRIPE_SECRET_KEY.",
        )

    tier_cfg = SUBSCRIPTION_TIERS.get(tier)
    if not tier_cfg:
        raise HTTPException(status_code=400, detail=f"Unknown tier '{tier}'. Choose: {list(SUBSCRIPTION_TIERS.keys())}")

    billing_period = tier_cfg.get("billing_period", "month")  # "month" or "year"
    # B23: Get localized price and currency
    currency = locale_to_currency(locale)
    localized_price = get_localized_price(tier_cfg["price_usd"], locale)
    price_cents = _price_cents(localized_price)

    # B14: Apply promo code
    discount_percent = 0
    discount_cents = 0
    discounts = []
    if promo:
        promo_code = apply_promo_code(db, promo)
        if promo_code:
            discount_percent = promo_code.discount_percent
            discount_cents = int(price_cents * discount_percent / 100)
            price_cents = price_cents - discount_cents
            # In Stripe, discounts are applied differently for subscriptions
            # For simplicity, we adjust the price; for production, use Stripe coupons
        else:
            raise HTTPException(status_code=400, detail="Invalid or expired promo code.")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "recurring": {"interval": billing_period, "interval_count": 1},
                    "unit_amount": price_cents,
                    "product_data": {
                        "name": f"Persona Hub — {tier_cfg['label']}",
                        "description": (
                            f"{tier_cfg['monthly_requests'] or 'Unlimited'} API calls/month. "
                            f"Billing: {'Annually' if billing_period == 'year' else 'Monthly'}"
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
                "billing_period": billing_period,
                "discount_percent": discount_percent,
                "referrer_id": referrer_id or "",  # B21: referrer for credit issuance
            },
            customer_email=user.email,
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "tier": tier,
            "billing_period": billing_period,
            "discount_percent": discount_percent,
        }
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
