"""
Database models — SQLite for MVP, PostgreSQL-ready via SQLAlchemy.

Swap DATABASE_URL env var to move to Postgres:
  DATABASE_URL=postgresql://user:pass@host/dbname
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey,
    Integer, Index, create_engine, UniqueConstraint, JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker, Session

_pwd_hasher = PasswordHasher()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./persona_store.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def hash_api_key(key: str) -> str:
    """SHA-256 hash of an API key for secure at-rest storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(stored_hash: str, provided_key: str) -> bool:
    return hashlib.sha256(provided_key.encode()).hexdigest() == stored_hash


def hash_password(password: str) -> str:
    """Argon2 hash for user passwords."""
    return _pwd_hasher.hash(password)


def verify_password(stored_hash: str, provided: str) -> bool:
    """Verify password against Argon2 hash."""
    try:
        _pwd_hasher.verify(stored_hash, provided)
        return True
    except VerifyMismatchError:
        return False


# ── Models ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id                = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    email             = Column(String(254), unique=True, nullable=False, index=True)
    # api_key stores the lookup prefix (first 20 chars of the full key).
    # The full key is shown to the user ONCE and never stored.
    api_key           = Column(String(64), unique=True, nullable=False, index=True)
    # SHA-256 hash of the full key for secure verification.
    api_key_hash      = Column(String(64), nullable=True, index=True)
    # Optional password for /auth/login (in addition to API key auth)
    password_hash     = Column(String(255), nullable=True)
    created_at        = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    active            = Column(Boolean, default=True)
    deleted_at        = Column(DateTime, nullable=True)
    email_verified    = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    # Failed login tracking (for rate limiting / lockout)
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login_at  = Column(DateTime, nullable=True)
    lockout_until         = Column(DateTime, nullable=True)
    # Stripe integration
    stripe_customer_id = Column(String(128), nullable=True, unique=True, index=True)

    purchases             = relationship("Purchase", back_populates="user", lazy="select")
    usage_logs            = relationship("APIKeyUsage", back_populates="user", lazy="select")
    subscription          = relationship("Subscription", back_populates="user", uselist=False, lazy="select")
    verification_tokens   = relationship("EmailVerificationToken", back_populates="user", lazy="select")
    login_attempts        = relationship("LoginAttempt", back_populates="user", lazy="select")
    invoices              = relationship("Invoice", back_populates="user", lazy="select")
    wallet                = relationship("Wallet", back_populates="user", uselist=False, lazy="select")
    referral_code         = relationship("ReferralCode", back_populates="referrer", uselist=False, lazy="select")
    referral_credits_given = relationship("ReferralCredit", foreign_keys="ReferralCredit.referrer_id", back_populates="referrer", lazy="select")
    referral_credits_received = relationship("ReferralCredit", foreign_keys="ReferralCredit.referee_id", back_populates="referee", lazy="select")

    @staticmethod
    def generate_api_key() -> str:
        """Generate a full API key. Caller stores only prefix + hash."""
        return "prs_" + secrets.token_hex(28)  # prs_ + 56 hex = 60 chars total


class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = (UniqueConstraint("user_id", "persona_id"),)

    id                = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    user_id           = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    persona_id        = Column(String(64), nullable=False)
    purchased_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    stripe_session_id = Column(String(128), nullable=True)
    amount_usd        = Column(Integer, nullable=True)  # cents
    deleted_at        = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="purchases")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id                     = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    user_id                = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tier                   = Column(String(16), nullable=False)    # "basic" | "pro"
    status                 = Column(String(16), default="active")  # "active" | "cancelled" | "expired"
    stripe_subscription_id = Column(String(128), nullable=True, unique=True)
    stripe_customer_id     = Column(String(128), nullable=True)
    requests_this_month    = Column(Integer, default=0)
    period_start           = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at             = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at             = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="subscription")


class StripeEvent(Base):
    """Idempotency log — prevents double-processing replayed webhooks."""
    __tablename__ = "stripe_events"

    id           = Column(String(64), primary_key=True)   # evt_xxx
    type         = Column(String(64), nullable=False)
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class APIKeyUsage(Base):
    __tablename__ = "api_key_usage"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    endpoint   = Column(String(200), nullable=False)
    persona_id = Column(String(64), nullable=True)
    platform   = Column(String(32), nullable=True)
    tier       = Column(String(16), nullable=True)
    timestamp  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="usage_logs")


class APIKeyRotation(Base):
    """Track API key rotations and revocations for audit trail."""
    __tablename__ = "api_key_rotation"

    id            = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    user_id       = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    api_key       = Column(String(64), unique=True, nullable=False, index=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deprecated_at = Column(DateTime, nullable=True)  # When rotated/revoked
    reason        = Column(String(64), nullable=True)  # "rotation" | "revocation" | "admin_revoke"

    user = relationship("User", foreign_keys=[user_id])


class EmailVerificationToken(Base):
    """One-time tokens for verifying email addresses."""
    __tablename__ = "email_verification_tokens"

    id         = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    user_id    = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token      = Column(String(96), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    used_at    = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="verification_tokens")


class AuditLog(Base):
    """Persistent audit trail for security and compliance events."""
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_user_ts", "user_id", "timestamp"),
        Index("ix_audit_log_event_type", "event_type"),
    )

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type  = Column(String(64), nullable=False)
    endpoint    = Column(String(256), nullable=True)
    method      = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    resource_id = Column(String(256), nullable=True)
    client_ip   = Column(String(45), nullable=True)
    timestamp   = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    details     = Column(String(1000), nullable=True)


class LoginAttempt(Base):
    """Track login attempts for failed login detection and IP-based rate limiting."""
    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_user_ip", "user_id", "client_ip", "attempted_at"),
    )

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_ip     = Column(String(45), nullable=False, index=True)
    success       = Column(Boolean, nullable=False)  # True = successful, False = failed
    attempted_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", back_populates="login_attempts")


# ── Payment Models ────────────────────────────────────────────────────────────

class Invoice(Base):
    """Stripe invoices — payment records for accounting and compliance."""
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_user_status", "user_id", "status"),
        Index("ix_invoices_stripe_id", "stripe_invoice_id"),
    )

    id                 = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    user_id            = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stripe_invoice_id  = Column(String(128), nullable=False, unique=True, index=True)
    amount_usd_cents   = Column(Integer, nullable=False)  # in cents
    status             = Column(String(16), nullable=False, server_default="draft", index=True)  # draft, open, paid, void
    issued_at          = Column(DateTime, nullable=False, index=True)
    due_at             = Column(DateTime, nullable=True)
    pdf_url            = Column(String(256), nullable=True)
    created_at         = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at         = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="invoices")


class Wallet(Base):
    """User credit balance for wallet-based payments."""
    __tablename__ = "wallets"

    id             = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    user_id        = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    balance_cents  = Column(Integer, nullable=False, server_default="0")  # in cents
    created_at     = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at     = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="wallet")


class ReferralCode(Base):
    """User-specific referral codes for referral program."""
    __tablename__ = "referral_codes"

    id           = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    referrer_id  = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code         = Column(String(16), nullable=False, unique=True, index=True)
    created_at   = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    referrer = relationship("User", back_populates="referral_code", foreign_keys=[referrer_id])


class ReferralCredit(Base):
    """Referral credit tracking — issued when referee makes a purchase."""
    __tablename__ = "referral_credits"
    __table_args__ = (
        Index("ix_referral_credits_referrer", "referrer_id", "status"),
        Index("ix_referral_credits_referee", "referee_id"),
    )

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id         = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    referee_id          = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    credit_amount_cents = Column(Integer, nullable=False)  # e.g., 500 = $5
    status              = Column(String(16), nullable=False, server_default="pending", index=True)  # pending, issued, used
    created_at          = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    used_at             = Column(DateTime, nullable=True)

    referrer = relationship("User", back_populates="referral_credits_given", foreign_keys=[referrer_id])
    referee = relationship("User", back_populates="referral_credits_received", foreign_keys=[referee_id])


class PromoCode(Base):
    """Promotional/coupon codes for discounts."""
    __tablename__ = "promo_codes"

    id                   = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    code                 = Column(String(64), nullable=False, unique=True, index=True)
    stripe_promotion_id  = Column(String(128), nullable=True, unique=True)
    discount_percent     = Column(Integer, nullable=False)  # 0-100
    status               = Column(String(16), nullable=False, server_default="active", index=True)  # active, expired, disabled
    expires_at           = Column(DateTime, nullable=True, index=True)
    max_redemptions      = Column(Integer, nullable=True)  # None = unlimited
    redemption_count     = Column(Integer, nullable=False, server_default="0")
    created_at           = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by           = Column(String(36), nullable=True)  # admin user_id


# ── Feature Flags (A/B Testing) ───────────────────────────────────────────────

class FeatureFlag(Base):
    """Server-side feature flags for gradual rollouts and A/B testing."""
    __tablename__ = "feature_flags"
    __table_args__ = (
        Index("ix_feature_flags_name_enabled", "name", "enabled"),
    )

    id                  = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    name                = Column(String(128), nullable=False, unique=True, index=True)
    description         = Column(String(500), nullable=True)
    enabled             = Column(Boolean, nullable=False, server_default="0", index=True)
    rollout_percentage  = Column(Integer, nullable=False, server_default="0")  # 0-100
    variants            = Column(JSON, nullable=False, server_default="[]")  # ["control", "variant_a", "variant_b"]
    targeted_user_ids   = Column(JSON, nullable=False, server_default="[]")  # ["usr_abc", "usr_def"]
    target_segments     = Column(JSON, nullable=False, server_default="[]")  # ["premium", "beta_testers"]
    target_tiers        = Column(JSON, nullable=False, server_default="[]")  # ["pro", "enterprise"]
    expires_at          = Column(DateTime, nullable=True, index=True)
    created_at          = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at          = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class FlagEvaluation(Base):
    """Analytics log for flag evaluations (A/B test metrics)."""
    __tablename__ = "flag_evaluations"
    __table_args__ = (
        Index("ix_flag_evaluations_flag_user", "flag_id", "user_id"),
        Index("ix_flag_evaluations_evaluated_at", "evaluated_at"),
    )

    id              = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    flag_id         = Column(String(36), ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         = Column(String(36), nullable=False, index=True)
    variant         = Column(String(64), nullable=False)  # "control", "variant_a", etc.
    enabled         = Column(Boolean, nullable=False)
    evaluated_at    = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


# ── Performance Monitoring (H93) ──────────────────────────────────────────────

class PerformanceMetric(Base):
    """Performance metrics for regression detection."""
    __tablename__ = "performance_metrics"
    __table_args__ = (
        Index("ix_performance_metrics_type_endpoint", "metric_type", "endpoint"),
        Index("ix_performance_metrics_recorded_at", "recorded_at"),
    )

    id              = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    metric_type     = Column(String(64), nullable=False, index=True)  # response_time_ms, error_rate_percent, etc.
    value           = Column(Integer, nullable=False)  # Metric value (milliseconds, percent, etc.)
    endpoint        = Column(String(256), nullable=True, index=True)  # API endpoint (optional)
    tags            = Column(JSON, nullable=False, server_default="{}")  # Additional metadata
    recorded_at     = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


class PerformanceBaseline(Base):
    """Baseline performance metrics for regression detection."""
    __tablename__ = "performance_baselines"
    __table_args__ = (
        Index("ix_performance_baselines_type_endpoint", "metric_type", "endpoint"),
        Index("ix_performance_baselines_created_at", "created_at"),
    )

    id              = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    metric_type     = Column(String(64), nullable=False, index=True)
    endpoint        = Column(String(256), nullable=True)
    p50             = Column(Integer, nullable=False)  # 50th percentile
    p95             = Column(Integer, nullable=False)  # 95th percentile (main metric)
    p99             = Column(Integer, nullable=False)  # 99th percentile
    mean            = Column(Integer, nullable=False)
    stddev          = Column(Integer, nullable=False)  # Standard deviation
    min_val         = Column(Integer, nullable=False)
    max_val         = Column(Integer, nullable=False)
    sample_count    = Column(Integer, nullable=False)  # Number of samples used
    created_at      = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


# ── Init ───────────────────────────────────────────────────────────────────────

def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── API Key helpers ───────────────────────────────────────────────────────────

def get_user_by_api_key(db: Session, api_key: str) -> "User | None":
    """Resolve an API key to a user. Supports hash-based (new) and prefix-fallback lookup."""
    key_hash = hash_api_key(api_key)
    # Primary: hash-based lookup (secure)
    user = db.query(User).filter(
        User.api_key_hash == key_hash,
        User.active == True,
        User.deleted_at == None,
    ).first()
    if user:
        return user
    # Fallback: legacy plaintext lookup for keys not yet migrated
    return db.query(User).filter(
        User.api_key == api_key,
        User.active == True,
        User.deleted_at == None,
    ).first()


def get_user_by_email(db: Session, email: str) -> "User | None":
    return db.query(User).filter(User.email == email, User.deleted_at == None).first()


def create_user(db: Session, email: str) -> tuple["User", str]:
    """Create a user. Returns (user, full_api_key) — caller must show the key to the user ONCE."""
    full_key = User.generate_api_key()
    prefix = full_key[:20]   # Display prefix only stored in DB
    key_hash = hash_api_key(full_key)

    user = User(email=email, api_key=prefix, api_key_hash=key_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, full_key


# ── Email verification helpers ────────────────────────────────────────────────

def create_email_verification_token(db: Session, user_id: str) -> str:
    """Generate and persist a 24-hour email verification token. Returns the raw token."""
    token = secrets.token_urlsafe(48)
    record = EmailVerificationToken(
        user_id=user_id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(record)
    db.commit()
    return token


def consume_verification_token(db: Session, token: str) -> "User | None":
    """Validate token, mark as used, set user.email_verified. Returns user or None."""
    now = datetime.now(timezone.utc)
    record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token,
        EmailVerificationToken.used_at == None,
        EmailVerificationToken.expires_at > now,
    ).first()
    if record is None:
        return None
    record.used_at = now
    user = db.query(User).filter(User.id == record.user_id).first()
    if user:
        user.email_verified = True
        user.email_verified_at = now
    db.commit()
    return user


def has_pending_verification(db: Session, user_id: str) -> bool:
    now = datetime.now(timezone.utc)
    return db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user_id,
        EmailVerificationToken.used_at == None,
        EmailVerificationToken.expires_at > now,
    ).first() is not None


# ── Audit log helpers ─────────────────────────────────────────────────────────

def write_audit_log(
    db: Session,
    event_type: str,
    user_id: str | None = None,
    endpoint: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    resource_id: str | None = None,
    client_ip: str | None = None,
    details: str | None = None,
) -> None:
    """Write a security event to the persistent audit log table."""
    try:
        entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            resource_id=resource_id,
            client_ip=client_ip,
            details=details,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()


# ── Purchase helpers ──────────────────────────────────────────────────────────

def has_purchased(db: Session, user_id: str, persona_id: str) -> bool:
    return db.query(Purchase).filter(
        Purchase.user_id == user_id,
        Purchase.persona_id == persona_id,
        Purchase.deleted_at == None,
    ).first() is not None


def record_purchase(
    db: Session,
    user_id: str,
    persona_id: str,
    stripe_session_id: str | None = None,
    amount_cents: int | None = None,
) -> Purchase:
    purchase = Purchase(
        user_id=user_id,
        persona_id=persona_id,
        stripe_session_id=stripe_session_id,
        amount_usd=amount_cents,
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase


# ── Subscription tier limits ──────────────────────────────────────────────────

SUBSCRIPTION_TIERS = {
    "basic_monthly": {"price_usd": 9.0,   "monthly_requests": 1000,  "billing_period": "month", "label": "Basic Monthly"},
    "basic_annual":  {"price_usd": 99.0,  "monthly_requests": 1000,  "billing_period": "year",  "label": "Basic Annual"},  # 20% discount
    "pro_monthly":   {"price_usd": 29.0,  "monthly_requests": None,  "billing_period": "month", "label": "Pro Monthly"},
    "pro_annual":    {"price_usd": 290.0, "monthly_requests": None,  "billing_period": "year",  "label": "Pro Annual"},    # 20% discount
    # Legacy tiers (for backward compatibility)
    "basic": {"price_usd": 9.0,  "monthly_requests": 1000,  "label": "Basic"},
    "pro":   {"price_usd": 29.0, "monthly_requests": None,   "label": "Pro"},   # None = unlimited
}


def get_subscription(db: Session, user_id: str) -> "Subscription | None":
    return db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == "active",
        Subscription.deleted_at == None,
    ).first()


def upsert_subscription(
    db: Session,
    user_id: str,
    tier: str,
    stripe_subscription_id: str | None = None,
    stripe_customer_id: str | None = None,
) -> "Subscription":
    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.deleted_at == None,
    ).first()
    if sub:
        sub.tier = tier
        sub.status = "active"
        if stripe_subscription_id:
            sub.stripe_subscription_id = stripe_subscription_id
        if stripe_customer_id:
            sub.stripe_customer_id = stripe_customer_id
        sub.requests_this_month = 0
        sub.period_start = datetime.now(timezone.utc)
    else:
        sub = Subscription(
            user_id=user_id,
            tier=tier,
            status="active",
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
        )
        db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def cancel_subscription(db: Session, user_id: str) -> bool:
    sub = get_subscription(db, user_id)
    if not sub:
        return False
    sub.status = "cancelled"
    db.commit()
    return True


def increment_request_count(db: Session, user_id: str) -> int:
    """Increment monthly request counter. Returns new count."""
    sub = get_subscription(db, user_id)
    if not sub:
        return 0
    sub.requests_this_month = (sub.requests_this_month or 0) + 1
    db.commit()
    return sub.requests_this_month


def check_quota(db: Session, user_id: str) -> dict:
    """Return quota status for the user."""
    sub = get_subscription(db, user_id)
    if not sub:
        return {"has_subscription": False, "tier": None, "allowed": False}

    tier_cfg = SUBSCRIPTION_TIERS.get(sub.tier, {})
    limit = tier_cfg.get("monthly_requests")
    used = sub.requests_this_month or 0

    if limit is None:
        allowed = True
    else:
        allowed = used < limit

    return {
        "has_subscription": True,
        "tier": sub.tier,
        "status": sub.status,
        "used": used,
        "limit": limit,
        "allowed": allowed,
    }


def log_usage(
    db: Session,
    user_id: str,
    endpoint: str,
    persona_id: str | None = None,
    platform: str | None = None,
    tier: str | None = None,
) -> None:
    log = APIKeyUsage(
        user_id=user_id,
        endpoint=endpoint,
        persona_id=persona_id,
        platform=platform,
        tier=tier,
    )
    db.add(log)
    db.commit()


def is_stripe_event_processed(db: Session, event_id: str) -> bool:
    return db.query(StripeEvent).filter(StripeEvent.id == event_id).first() is not None


def mark_stripe_event_processed(db: Session, event_id: str, event_type: str) -> None:
    db.add(StripeEvent(id=event_id, type=event_type))
    db.commit()


# ── Login attempt tracking & lockout ──────────────────────────────────────────

def record_login_attempt(
    db: Session,
    user_id: str,
    client_ip: str,
    success: bool,
) -> None:
    """Record a login attempt for failed login tracking and rate limiting."""
    attempt = LoginAttempt(user_id=user_id, client_ip=client_ip, success=success)
    db.add(attempt)

    if not success:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            user.last_failed_login_at = datetime.now(timezone.utc)

            if user.failed_login_attempts >= 5:
                user.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=5)

    db.commit()


def check_lockout(user: User) -> bool:
    """Check if user is currently locked out due to failed login attempts."""
    if user.lockout_until is None:
        return False
    now = datetime.now(timezone.utc)
    # Handle both timezone-aware and naive datetimes
    lockout = user.lockout_until
    if lockout.tzinfo is None:
        lockout = lockout.replace(tzinfo=timezone.utc)
    if now < lockout:
        return True
    user.lockout_until = None
    user.failed_login_attempts = 0
    return False


def clear_login_attempts(db: Session, user_id: str) -> None:
    """Clear failed login counter after successful login."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.failed_login_attempts = 0
        user.last_failed_login_at = None
        user.lockout_until = None
        db.commit()


# ── Wallet helpers ────────────────────────────────────────────────────────────

def get_or_create_wallet(db: Session, user_id: str) -> Wallet:
    """Get or create a wallet for a user."""
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(id=secrets.token_hex(16), user_id=user_id, balance_cents=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


def add_wallet_credit(db: Session, user_id: str, amount_cents: int) -> Wallet:
    """Add credit to a user's wallet."""
    wallet = get_or_create_wallet(db, user_id)
    wallet.balance_cents = (wallet.balance_cents or 0) + amount_cents
    wallet.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(wallet)
    return wallet


def deduct_wallet_credit(db: Session, user_id: str, amount_cents: int) -> bool:
    """Deduct credit from wallet. Returns True if successful, False if insufficient balance."""
    wallet = get_or_create_wallet(db, user_id)
    if (wallet.balance_cents or 0) < amount_cents:
        return False
    wallet.balance_cents = (wallet.balance_cents or 0) - amount_cents
    wallet.updated_at = datetime.now(timezone.utc)
    db.commit()
    return True


# ── Referral helpers ──────────────────────────────────────────────────────────

def generate_referral_code(db: Session, user_id: str) -> str:
    """Generate or return existing referral code for a user."""
    existing = db.query(ReferralCode).filter(ReferralCode.referrer_id == user_id).first()
    if existing:
        return existing.code
    # Generate a short, unique code (6-8 chars)
    code = secrets.token_hex(3)  # 6 hex chars
    while db.query(ReferralCode).filter(ReferralCode.code == code).first():
        code = secrets.token_hex(3)
    ref_code = ReferralCode(id=secrets.token_hex(16), referrer_id=user_id, code=code)
    db.add(ref_code)
    db.commit()
    return code


def get_referral_code_by_code(db: Session, code: str) -> "ReferralCode | None":
    """Lookup a referral code by code string."""
    return db.query(ReferralCode).filter(ReferralCode.code == code).first()


def issue_referral_credit(db: Session, referrer_id: str, referee_id: str, amount_cents: int = 500) -> ReferralCredit:
    """Issue a referral credit when referee makes a purchase. Amount defaults to $5 (500 cents)."""
    credit = ReferralCredit(
        referrer_id=referrer_id,
        referee_id=referee_id,
        credit_amount_cents=amount_cents,
        status="issued",
    )
    db.add(credit)
    db.commit()
    db.refresh(credit)
    # Also add to referrer's wallet
    add_wallet_credit(db, referrer_id, amount_cents)
    return credit


# ── Invoice helpers ───────────────────────────────────────────────────────────

def record_invoice(
    db: Session,
    user_id: str,
    stripe_invoice_id: str,
    amount_usd_cents: int,
    status: str = "open",
    issued_at: datetime | None = None,
    due_at: datetime | None = None,
    pdf_url: str | None = None,
) -> Invoice:
    """Record a Stripe invoice in the database."""
    if issued_at is None:
        issued_at = datetime.now(timezone.utc)
    invoice = Invoice(
        id=secrets.token_hex(16),
        user_id=user_id,
        stripe_invoice_id=stripe_invoice_id,
        amount_usd_cents=amount_usd_cents,
        status=status,
        issued_at=issued_at,
        due_at=due_at,
        pdf_url=pdf_url,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def get_user_invoices(db: Session, user_id: str, limit: int = 50) -> list[Invoice]:
    """Get recent invoices for a user."""
    return db.query(Invoice).filter(Invoice.user_id == user_id).order_by(Invoice.issued_at.desc()).limit(limit).all()


# ── Promo code helpers ────────────────────────────────────────────────────────

def get_promo_code(db: Session, code: str) -> "PromoCode | None":
    """Get a promo code if it exists and is still valid."""
    promo = db.query(PromoCode).filter(
        PromoCode.code == code,
        PromoCode.status == "active",
    ).first()
    if not promo:
        return None
    # Check expiration
    if promo.expires_at:
        now = datetime.now(timezone.utc)
        expires_at = promo.expires_at
        # Handle both naive and aware datetimes
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            return None
    # Check max redemptions
    if promo.max_redemptions and promo.redemption_count >= promo.max_redemptions:
        return None
    return promo


def apply_promo_code(db: Session, code: str) -> "PromoCode | None":
    """Apply a promo code (increment redemption count). Returns promo code or None if invalid."""
    promo = get_promo_code(db, code)
    if not promo:
        return None
    promo.redemption_count = (promo.redemption_count or 0) + 1
    db.commit()
    db.refresh(promo)
    return promo


# ── Free tier helpers ─────────────────────────────────────────────────────────

def grant_free_persona(db: Session, user_id: str, persona_id: str = "persona_socrates") -> Purchase:
    """Grant a free persona to a new user."""
    purchase = record_purchase(db, user_id, persona_id, amount_cents=0)
    return purchase


# ── Bundle pricing (B15) ──────────────────────────────────────────────────────

BUNDLE_PRICING = {
    "bundle_10": {
        "name": "Starter Bundle",
        "personas": 10,
        "price_usd": 49.0,
        "savings_pct": 8,
        "description": "10 personas at a discount"
    },
    "bundle_50": {
        "name": "Professional Bundle",
        "personas": 50,
        "price_usd": 199.0,
        "savings_pct": 20,
        "description": "50 personas at 20% savings"
    },
    "bundle_495": {
        "name": "Complete Library",
        "personas": 495,
        "price_usd": 999.0,
        "savings_pct": 50,
        "description": "All 495 personas in the library"
    },
}
