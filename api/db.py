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
    Integer, Index, create_engine, UniqueConstraint,
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

    purchases             = relationship("Purchase", back_populates="user", lazy="select")
    usage_logs            = relationship("APIKeyUsage", back_populates="user", lazy="select")
    subscription          = relationship("Subscription", back_populates="user", uselist=False, lazy="select")
    verification_tokens   = relationship("EmailVerificationToken", back_populates="user", lazy="select")
    login_attempts        = relationship("LoginAttempt", back_populates="user", lazy="select")

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
