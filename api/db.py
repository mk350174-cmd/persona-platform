"""
SQLAlchemy models + session. SQLite by default (dev); set DATABASE_URL for
PostgreSQL in production (ADR 0001 — FastAPI+PostgreSQL, T2-001).
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone

from sqlalchemy import create_engine, String, DateTime, Date, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./persona_platform.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Note: `date_of_birth` was added after the first version of this table
    (T2-054), and `oauth_provider`/`oauth_id` after that (T2-008).
    init_db() only creates missing tables, it does not ALTER existing ones
    — no Alembic migration tooling is wired up yet (no real production
    database exists to migrate). A pre-existing local dev
    persona_platform.db needs to be deleted and recreated to pick these up.

    OAuth-created accounts have no password (`password_hash` is None) and
    no date_of_birth until the user submits one via PATCH /auth/me/date-of-
    birth — neither Google's nor GitHub's OAuth userinfo reliably includes
    a verified birthdate, so age verification (T2-054) can't happen inside
    the OAuth callback itself. `date_of_birth is None` is the "still needs
    age verification" signal for OAuth accounts specifically; password-
    registered accounts always have it set at signup (RegisterRequest
    requires it) and can never be None."""
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth_identity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "google" | "github" | None
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user")
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="user")


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    key_preview: Mapped[str] = mapped_column(String(20))  # e.g. "prs_ab12...cd34"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="api_keys")


class Purchase(Base):
    """A user's access grant to one persona (test-mode Stripe checkout, T2-021)."""
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    persona_id: Mapped[str] = mapped_column(String(64))
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_payment_status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="purchases")


class ChatMessage(Base):
    """Persisted chat turn (T2-019 memory layer — minimal version)."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    persona_id: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16))  # "user" | "persona"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
