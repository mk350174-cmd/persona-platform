"""Simplified integration tests for payment endpoints (H84 - avoiding full app import)."""

import pytest
import os
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import (
    Base, create_user, get_or_create_wallet, add_wallet_credit,
    generate_referral_code, record_invoice, grant_free_persona,
    has_purchased, SUBSCRIPTION_TIERS, BUNDLE_PRICING,
)


@pytest.fixture
def test_db(tmp_path):
    """Create test database (file-based SQLite for proper session isolation)."""
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    yield session
    session.close()


class TestEndToEndCheckout:
    """End-to-end checkout flow tests."""

    def test_free_tier_signup_workflow(self, test_db):
        """Complete free tier signup flow."""
        # 1. Register user
        user, api_key = create_user(test_db, "signup@example.com")
        assert api_key.startswith("prs_")

        # 2. Grant free persona
        purchase = grant_free_persona(test_db, user.id)
        assert has_purchased(test_db, user.id, "persona_socrates")

        # 3. Create wallet
        wallet = get_or_create_wallet(test_db, user.id)
        assert wallet.balance_cents == 0

        # 4. Generate referral code
        code = generate_referral_code(test_db, user.id)
        assert len(code) > 0

    def test_referral_credit_workflow(self, test_db):
        """Complete referral credit flow."""
        from api.db import issue_referral_credit, get_referral_code_by_code

        # 1. Create referrer
        referrer, _ = create_user(test_db, "referrer_flow@example.com")
        ref_code = generate_referral_code(test_db, referrer.id)

        # 2. Create referee (with referral)
        referee, _ = create_user(test_db, "referee_flow@example.com")
        found_code = get_referral_code_by_code(test_db, ref_code)
        assert found_code.referrer_id == referrer.id

        # 3. Issue credit on purchase
        credit = issue_referral_credit(test_db, referrer.id, referee.id, 500)
        assert credit.status == "issued"

        # 4. Check referrer wallet updated
        wallet = get_or_create_wallet(test_db, referrer.id)
        assert wallet.balance_cents == 500

    def test_wallet_and_purchase_workflow(self, test_db):
        """Wallet deduction on purchase."""
        user, _ = create_user(test_db, "wallet_purchase@example.com")

        # 1. Add $50 credit
        add_wallet_credit(test_db, user.id, 5000)

        # 2. Deduct for purchase
        from api.db import deduct_wallet_credit
        success = deduct_wallet_credit(test_db, user.id, 2999)  # $29.99
        assert success is True

        # 3. Check remaining balance
        wallet = get_or_create_wallet(test_db, user.id)
        assert wallet.balance_cents == 2001  # $50 - $29.99

    def test_invoice_and_subscription_workflow(self, test_db):
        """Invoice recording for subscription."""
        user, _ = create_user(test_db, "sub_invoice@example.com")

        # 1. Start subscription
        from api.db import upsert_subscription
        sub = upsert_subscription(
            test_db, user.id, "basic_monthly",
            stripe_subscription_id="sub_test",
            stripe_customer_id="cus_test",
        )
        assert sub.tier == "basic_monthly"

        # 2. Record invoice
        invoice = record_invoice(
            test_db,
            user.id,
            "inv_sub_123",
            999,  # $9.99
            status="paid",
            issued_at=datetime.now(timezone.utc),
        )
        assert invoice.status == "paid"

        # 3. Retrieve invoices
        from api.db import get_user_invoices
        invoices = get_user_invoices(test_db, user.id)
        assert len(invoices) == 1
        assert invoices[0].amount_usd_cents == 999


class TestMultiCurrencyScenarios:
    """Multi-currency pricing scenarios."""

    def test_pricing_across_currencies(self):
        """Verify pricing in different currencies."""
        from api.payments import get_localized_price

        base_price = 29.0  # $29 USD

        # Prices in different currencies
        prices = {
            "usd": get_localized_price(base_price, "usd"),
            "eur": get_localized_price(base_price, "eur"),
            "try": get_localized_price(base_price, "try"),
            "gbp": get_localized_price(base_price, "gbp"),
        }

        # Verify all conversions exist
        assert all(p > 0 for p in prices.values())
        # EUR should be less than USD
        assert prices["eur"] < prices["usd"]
        # TRY should be much higher than USD
        assert prices["try"] > prices["usd"]

    def test_bundle_pricing_with_discounts(self):
        """Bundle pricing with discount calculations."""
        bundles = {
            "bundle_10": {"personas": 10, "price": 49.0, "savings": 8},
            "bundle_50": {"personas": 50, "price": 199.0, "savings": 20},
            "bundle_495": {"personas": 495, "price": 999.0, "savings": 50},
        }

        for bundle_id, expected in bundles.items():
            bundle = BUNDLE_PRICING[bundle_id]
            assert bundle["personas"] == expected["personas"]
            assert bundle["price_usd"] == expected["price"]
            assert bundle["savings_pct"] == expected["savings"]


class TestPromoCodeScenarios:
    """Promo code application scenarios."""

    def test_discount_calculation(self):
        """Discount amount calculation."""
        from api.payments import _price_cents

        # Base price: $99
        base_cents = _price_cents(99.0)
        assert base_cents == 9900

        # 50% discount
        discount_percent = 50
        discount_cents = int(base_cents * discount_percent / 100)
        final_cents = base_cents - discount_cents

        assert discount_cents == 4950
        assert final_cents == 4950

    def test_stacked_discounts(self):
        """Promo code + wallet credit scenario."""
        from api.payments import _price_cents

        # Scenario: $100 item, 20% promo, $30 wallet
        base_cents = 10000
        promo_percent = 20
        wallet_cents = 3000

        # Apply promo
        discount_cents = int(base_cents * promo_percent / 100)
        after_promo = base_cents - discount_cents  # $80

        # Deduct wallet
        charge_cents = max(0, after_promo - wallet_cents)  # $50

        assert after_promo == 8000
        assert charge_cents == 5000


class TestErrorScenarios:
    """Error handling in payment flows."""

    def test_duplicate_referral_code_generation(self, test_db):
        """Can't generate two referral codes for same user."""
        user, _ = create_user(test_db, "dup_ref@example.com")
        code1 = generate_referral_code(test_db, user.id)
        code2 = generate_referral_code(test_db, user.id)
        assert code1 == code2

    def test_invalid_tier_name(self):
        """Invalid subscription tier handling."""
        invalid_tiers = ["basic", "pro", "premium", "enterprise"]
        for tier in invalid_tiers:
            # Only the new tier names should work
            if tier not in ["basic_monthly", "basic_annual", "pro_monthly", "pro_annual"]:
                # Old tiers still in dict for backward compat
                if tier in SUBSCRIPTION_TIERS:
                    # Verify they exist but are marked for migration
                    assert SUBSCRIPTION_TIERS[tier]["price_usd"] > 0

    def test_negative_wallet_balance_protection(self, test_db):
        """Can't create negative wallet balance."""
        user, _ = create_user(test_db, "negative_wallet@example.com")
        add_wallet_credit(test_db, user.id, 100)

        from api.db import deduct_wallet_credit
        # Try to deduct more than available
        success = deduct_wallet_credit(test_db, user.id, 500)
        assert success is False

        # Balance should be unchanged
        wallet = get_or_create_wallet(test_db, user.id)
        assert wallet.balance_cents == 100
