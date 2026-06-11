"""Unit tests for payment functions (no app import)."""

import pytest
from datetime import datetime, timezone

from api.db import (
    SessionLocal, init_db, create_user, get_or_create_wallet,
    add_wallet_credit, deduct_wallet_credit, generate_referral_code,
    get_referral_code_by_code, issue_referral_credit, record_invoice,
    get_promo_code, apply_promo_code, grant_free_persona,
    SUBSCRIPTION_TIERS, BUNDLE_PRICING, has_purchased, Purchase,
)
from api.payments import (
    _price_cents, locale_to_currency, get_localized_price,
)


class TestPricing:
    """Unit tests for pricing functions."""

    def test_price_cents_conversion(self):
        """Convert USD to cents."""
        assert _price_cents(9.99) == 999
        assert _price_cents(99.0) == 9900
        assert _price_cents(0.5) == 50

    def test_locale_to_currency(self):
        """Map locale to Stripe currency code."""
        assert locale_to_currency("usd") == "usd"
        assert locale_to_currency("eur") == "eur"
        assert locale_to_currency("try") == "try"
        assert locale_to_currency("gbp") == "gbp"
        # Case insensitive
        assert locale_to_currency("USD") == "usd"
        assert locale_to_currency("EUR") == "eur"

    def test_localized_price(self):
        """Convert price to different currencies."""
        # 1 USD baseline
        usd = get_localized_price(10.0, "usd")
        assert usd == 10.0

        # EUR is ~0.92x USD
        eur = get_localized_price(10.0, "eur")
        assert 9.0 < eur < 9.5

        # TRY is ~32.5x USD
        try_price = get_localized_price(10.0, "try")
        assert 320.0 < try_price < 330.0

        # GBP is ~0.79x USD
        gbp = get_localized_price(10.0, "gbp")
        assert 7.5 < gbp < 8.0


class TestSubscriptionTiers:
    """Unit tests for subscription tier configuration."""

    def test_tiers_exist(self):
        """All required subscription tiers are configured."""
        required = ["basic_monthly", "basic_annual", "pro_monthly", "pro_annual"]
        for tier in required:
            assert tier in SUBSCRIPTION_TIERS
            cfg = SUBSCRIPTION_TIERS[tier]
            assert "price_usd" in cfg
            assert "billing_period" in cfg

    def test_annual_discount(self):
        """Annual tiers have 20% discount vs monthly."""
        basic_monthly = SUBSCRIPTION_TIERS["basic_monthly"]["price_usd"]
        basic_annual = SUBSCRIPTION_TIERS["basic_annual"]["price_usd"]
        # Annual should be ~20% less than 12x monthly
        assert basic_annual < basic_monthly * 12 * 0.95

        pro_monthly = SUBSCRIPTION_TIERS["pro_monthly"]["price_usd"]
        pro_annual = SUBSCRIPTION_TIERS["pro_annual"]["price_usd"]
        assert pro_annual < pro_monthly * 12 * 0.95

    def test_billing_period_values(self):
        """Billing periods are valid."""
        for tier, cfg in SUBSCRIPTION_TIERS.items():
            if "billing_period" in cfg:
                assert cfg["billing_period"] in ["month", "year"]


class TestBundlePricing:
    """Unit tests for bundle pricing."""

    def test_bundles_exist(self):
        """All bundle tiers are configured."""
        required = ["bundle_10", "bundle_50", "bundle_495"]
        for bundle in required:
            assert bundle in BUNDLE_PRICING
            cfg = BUNDLE_PRICING[bundle]
            assert "personas" in cfg
            assert "price_usd" in cfg
            assert "savings_pct" in cfg

    def test_bundle_savings(self):
        """Bundle pricing offers meaningful discounts."""
        for bundle_id, cfg in BUNDLE_PRICING.items():
            assert cfg["savings_pct"] > 0, f"{bundle_id} should have savings"
            assert cfg["savings_pct"] <= 50, f"{bundle_id} savings should be realistic"


@pytest.fixture
def db(tmp_path):
    """Create file-based SQLite DB for testing (parallel-safe)."""
    from sqlalchemy import create_engine
    from api.db import Base
    from sqlalchemy.orm import sessionmaker

    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal_local()
    yield session
    session.close()


class TestWalletOperations:
    """Unit tests for wallet functions."""

    def test_create_wallet(self, db):
        """Create wallet for user."""
        user, _ = create_user(db, "wallet_test@example.com")
        wallet = get_or_create_wallet(db, user.id)
        assert wallet.user_id == user.id
        assert wallet.balance_cents == 0

    def test_add_wallet_credit(self, db):
        """Add credit to wallet."""
        user, _ = create_user(db, "wallet_add@example.com")
        wallet = add_wallet_credit(db, user.id, 500)  # $5
        assert wallet.balance_cents == 500

        wallet = add_wallet_credit(db, user.id, 1000)  # +$10
        assert wallet.balance_cents == 1500

    def test_deduct_wallet_credit(self, db):
        """Deduct credit from wallet."""
        user, _ = create_user(db, "wallet_deduct@example.com")
        add_wallet_credit(db, user.id, 1000)  # $10

        success = deduct_wallet_credit(db, user.id, 500)  # $5
        assert success is True
        wallet = get_or_create_wallet(db, user.id)
        assert wallet.balance_cents == 500

    def test_insufficient_balance(self, db):
        """Deduction fails if insufficient balance."""
        user, _ = create_user(db, "wallet_insufficient@example.com")
        add_wallet_credit(db, user.id, 100)  # $1

        success = deduct_wallet_credit(db, user.id, 500)  # Try $5
        assert success is False
        wallet = get_or_create_wallet(db, user.id)
        assert wallet.balance_cents == 100  # Unchanged


class TestReferralProgram:
    """Unit tests for referral functions."""

    def test_generate_referral_code(self, db):
        """Generate unique referral code."""
        user, _ = create_user(db, "referrer@example.com")
        code = generate_referral_code(db, user.id)
        assert code is not None
        assert len(code) > 0

    def test_referral_code_idempotent(self, db):
        """Generating referral code twice returns same code."""
        user, _ = create_user(db, "referrer_dup@example.com")
        code1 = generate_referral_code(db, user.id)
        code2 = generate_referral_code(db, user.id)
        assert code1 == code2

    def test_get_referral_code(self, db):
        """Lookup referral code by code string."""
        user, _ = create_user(db, "referrer_lookup@example.com")
        code = generate_referral_code(db, user.id)
        found = get_referral_code_by_code(db, code)
        assert found is not None
        assert found.referrer_id == user.id

    def test_issue_referral_credit(self, db):
        """Issue credit to referrer on referee purchase."""
        referrer, _ = create_user(db, "referrer_credit@example.com")
        referee, _ = create_user(db, "referee@example.com")

        credit = issue_referral_credit(db, referrer.id, referee.id, 500)  # $5
        assert credit.status == "issued"
        assert credit.credit_amount_cents == 500

        # Check referrer's wallet was updated
        wallet = get_or_create_wallet(db, referrer.id)
        assert wallet.balance_cents == 500


class TestPromoCodes:
    """Unit tests for promo code functions."""

    def test_apply_promo_code(self, db):
        """Apply a promo code."""
        from api.db import PromoCode
        # Manually create a promo code
        promo = PromoCode(
            code="TEST50",
            discount_percent=50,
            status="active",
        )
        db.add(promo)
        db.commit()

        # Apply it
        applied = apply_promo_code(db, "TEST50")
        assert applied is not None
        assert applied.discount_percent == 50
        assert applied.redemption_count == 1

    def test_invalid_promo_code(self, db):
        """Invalid promo code returns None."""
        result = get_promo_code(db, "INVALID")
        assert result is None

    def test_expired_promo_code(self, db):
        """Expired promo code is rejected."""
        from api.db import PromoCode
        from datetime import timedelta

        past = datetime.now(timezone.utc) - timedelta(days=1)
        promo = PromoCode(
            code="EXPIRED",
            discount_percent=10,
            status="active",
            expires_at=past,
        )
        db.add(promo)
        db.commit()

        result = get_promo_code(db, "EXPIRED")
        assert result is None


class TestInvoices:
    """Unit tests for invoice functions."""

    def test_record_invoice(self, db):
        """Record a Stripe invoice."""
        user, _ = create_user(db, "invoice_user@example.com")
        invoice = record_invoice(
            db,
            user.id,
            "inv_stripe123",
            9900,  # $99
            status="paid",
            issued_at=datetime.now(timezone.utc),
        )
        assert invoice.stripe_invoice_id == "inv_stripe123"
        assert invoice.amount_usd_cents == 9900
        assert invoice.status == "paid"

    def test_invoice_retrieved(self, db):
        """Invoice can be retrieved from DB."""
        user, _ = create_user(db, "invoice_retrieve@example.com")
        recorded = record_invoice(
            db,
            user.id,
            "inv_test456",
            2999,
            status="open",
        )
        # Verify it's in DB
        from api.db import get_user_invoices
        invoices = get_user_invoices(db, user.id)
        assert len(invoices) == 1
        assert invoices[0].stripe_invoice_id == "inv_test456"


class TestFreeTier:
    """Unit tests for free tier grant."""

    def test_grant_free_persona(self, db):
        """Grant free persona to new user."""
        user, _ = create_user(db, "freetier@example.com")
        purchase = grant_free_persona(db, user.id, "persona_socrates")
        assert purchase.persona_id == "persona_socrates"
        assert purchase.amount_usd == 0
        assert has_purchased(db, user.id, "persona_socrates")
