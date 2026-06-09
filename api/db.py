"""
Database models — SQLite for MVP, PostgreSQL-ready via SQLAlchemy.

Swap DATABASE_URL env var to move to Postgres:
  DATABASE_URL=postgresql://user:pass@host/dbname
"""

import os
import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey,
    Integer, create_engine, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./persona_store.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# ── Models ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id         = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    email      = Column(String(254), unique=True, nullable=False, index=True)
    api_key    = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    active     = Column(Boolean, default=True)

    purchases    = relationship("Purchase", back_populates="user", lazy="select")
    usage_logs   = relationship("APIKeyUsage", back_populates="user", lazy="select")
    subscription = relationship("Subscription", back_populates="user", uselist=False, lazy="select")

    @staticmethod
    def generate_api_key() -> str:
        return "prs_" + secrets.token_hex(28)  # prs_ + 56 hex chars = 60 total


class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = (UniqueConstraint("user_id", "persona_id"),)

    id                 = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    user_id            = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    persona_id         = Column(String(64), nullable=False)
    purchased_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    stripe_session_id  = Column(String(128), nullable=True)
    amount_usd         = Column(Integer, nullable=True)  # cents

    user = relationship("User", back_populates="purchases")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id                      = Column(String(36), primary_key=True, default=lambda: secrets.token_hex(16))
    user_id                 = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tier                    = Column(String(16), nullable=False)   # "basic" | "pro"
    status                  = Column(String(16), default="active") # "active" | "cancelled" | "expired"
    stripe_subscription_id  = Column(String(128), nullable=True, unique=True)
    stripe_customer_id      = Column(String(128), nullable=True)
    requests_this_month     = Column(Integer, default=0)
    period_start            = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at              = Column(DateTime, default=lambda: datetime.now(timezone.utc))

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_user_by_api_key(db: Session, api_key: str) -> User | None:
    return db.query(User).filter(User.api_key == api_key, User.active).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str) -> User:
    user = User(email=email, api_key=User.generate_api_key())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def has_purchased(db: Session, user_id: str, persona_id: str) -> bool:
    return db.query(Purchase).filter(
        Purchase.user_id == user_id,
        Purchase.persona_id == persona_id,
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
    ).first()


def upsert_subscription(
    db: Session,
    user_id: str,
    tier: str,
    stripe_subscription_id: str | None = None,
    stripe_customer_id: str | None = None,
) -> "Subscription":
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
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
