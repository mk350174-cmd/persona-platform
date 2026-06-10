"""security_hardening — API key hashing, email verification, audit log, soft delete

Revision ID: a1b2c3d4e5f6
Revises: 98e96cff2d3b
Create Date: 2026-06-10 00:00:00.000000
"""

from typing import Sequence, Union
from datetime import datetime, timezone
import hashlib

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '98e96cff2d3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def upgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    # ── 1. users: api_key_hash, email_verified, email_verified_at, deleted_at ──

    if is_sqlite:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("api_key_hash", sa.String(64), nullable=True))
            batch_op.add_column(sa.Column("email_verified", sa.Boolean(), nullable=True, server_default="0"))
            batch_op.add_column(sa.Column("email_verified_at", sa.DateTime(), nullable=True))
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
    else:
        op.add_column("users", sa.Column("api_key_hash", sa.String(64), nullable=True))
        op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=True, server_default="false"))
        op.add_column("users", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
        op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # ── 2. Data migration: hash existing plaintext API keys, store prefix ──────

    users = conn.execute(sa.text("SELECT id, api_key FROM users")).fetchall()
    for user in users:
        full_key = user.api_key
        key_hash = _sha256(full_key)
        prefix = full_key[:20]
        conn.execute(
            sa.text("UPDATE users SET api_key_hash = :h, api_key = :p WHERE id = :id"),
            {"h": key_hash, "p": prefix, "id": user.id},
        )

    # Add index on api_key_hash
    op.create_index("ix_users_api_key_hash", "users", ["api_key_hash"], unique=False)

    # ── 3. purchases: deleted_at ───────────────────────────────────────────────

    if is_sqlite:
        with op.batch_alter_table("purchases") as batch_op:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
    else:
        op.add_column("purchases", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # ── 4. subscriptions: deleted_at ──────────────────────────────────────────

    if is_sqlite:
        with op.batch_alter_table("subscriptions") as batch_op:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
    else:
        op.add_column("subscriptions", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # ── 5. email_verification_tokens ──────────────────────────────────────────

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(96), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_evtokens_user_id", "email_verification_tokens", ["user_id"])
    op.create_index("ix_evtokens_token", "email_verification_tokens", ["token"], unique=True)

    # ── 6. audit_log ──────────────────────────────────────────────────────────

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("endpoint", sa.String(256), nullable=True),
        sa.Column("method", sa.String(10), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("resource_id", sa.String(256), nullable=True),
        sa.Column("client_ip", sa.String(45), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("details", sa.String(1000), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_user_ts", "audit_log", ["user_id", "timestamp"])
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])

    # ── 7. api_key_rotation table (create if missing) ─────────────────────────
    # Alembic may have not created this in the initial migration; guard with try.
    try:
        op.create_table(
            "api_key_rotation",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("api_key", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("deprecated_at", sa.DateTime(), nullable=True),
            sa.Column("reason", sa.String(64), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("api_key"),
        )
        op.create_index("ix_api_key_rotation_user_id", "api_key_rotation", ["user_id"])
        op.create_index("ix_api_key_rotation_api_key", "api_key_rotation", ["api_key"], unique=True)
    except Exception:
        pass  # Table already exists from a previous migration


def downgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    op.drop_table("audit_log")
    op.drop_table("email_verification_tokens")

    if is_sqlite:
        with op.batch_alter_table("subscriptions") as batch_op:
            batch_op.drop_column("deleted_at")
        with op.batch_alter_table("purchases") as batch_op:
            batch_op.drop_column("deleted_at")
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_index("ix_users_api_key_hash")
            batch_op.drop_column("api_key_hash")
            batch_op.drop_column("email_verified")
            batch_op.drop_column("email_verified_at")
            batch_op.drop_column("deleted_at")
    else:
        op.drop_index("ix_users_api_key_hash", table_name="users")
        op.drop_column("subscriptions", "deleted_at")
        op.drop_column("purchases", "deleted_at")
        op.drop_column("users", "api_key_hash")
        op.drop_column("users", "email_verified")
        op.drop_column("users", "email_verified_at")
        op.drop_column("users", "deleted_at")
