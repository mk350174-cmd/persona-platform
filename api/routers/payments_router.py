"""
Stripe checkout — test-mode only in this repo (T2-021/T2-023). A real
deployment provides STRIPE_SECRET_KEY (sk_live_...) via a secrets manager;
this code refuses to run with a live key unless STRIPE_ALLOW_LIVE=1 is
explicitly set, as a guardrail against accidentally charging real cards
from a dev/test environment.
"""

from __future__ import annotations

import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..persona_catalog import CATALOG
from ..schemas import CheckoutResponse
from ..deps import get_current_user
from ..db import get_db, User, Purchase

router = APIRouter(tags=["payments"])

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_dummy")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_test_dummy")
PERSONA_PRICE_USD_CENTS = 999  # $9.99 per persona, test-mode placeholder price


def _guard_live_key() -> None:
    if STRIPE_SECRET_KEY.startswith("sk_live_") and os.environ.get("STRIPE_ALLOW_LIVE") != "1":
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Refusing to use a live Stripe key without STRIPE_ALLOW_LIVE=1 "
            "(T2-023 guardrail — see api/routers/payments_router.py).",
        )


@router.post("/checkout/{persona_id}", response_model=CheckoutResponse)
def create_checkout(persona_id: str, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _guard_live_key()
    if persona_id not in CATALOG:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown persona: {persona_id}")
    stripe.api_key = STRIPE_SECRET_KEY

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": PERSONA_PRICE_USD_CENTS,
                "product_data": {"name": f"Persona access: {CATALOG[persona_id].name}"},
            },
            "quantity": 1,
        }],
        success_url="https://example.invalid/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://example.invalid/cancel",
        client_reference_id=str(user.id),
        metadata={"persona_id": persona_id, "user_id": str(user.id)},
    )
    purchase = Purchase(user_id=user.id, persona_id=persona_id,
                         stripe_checkout_session_id=session.id, stripe_payment_status="pending")
    db.add(purchase)
    db.commit()
    return CheckoutResponse(checkout_url=session.url, session_id=session.id,
                             test_mode=not STRIPE_SECRET_KEY.startswith("sk_live_"))


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Verify signature before touching the payload (T2-022)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        purchase = (
            db.query(Purchase)
            .filter(Purchase.stripe_checkout_session_id == session["id"])
            .first()
        )
        if purchase:
            purchase.stripe_payment_status = "paid"
            db.commit()
    return {"received": True}
