"""production_indexes — Add indexes for Postgres production queries

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-10 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add production-ready indexes for common queries."""
    conn = op.get_bind()

    # ── users table indexes ──────────────────────────────────────────────────

    try:
        op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    except Exception:
        pass

    # ── purchases table indexes ──────────────────────────────────────────────

    try:
        op.create_index("ix_purchases_persona_id", "purchases", ["persona_id"])
    except Exception:
        pass

    try:
        op.create_index(
            "ix_purchases_user_persona",
            "purchases",
            ["user_id", "persona_id"],
            unique=False,  # unique constraint already exists
        )
    except Exception:
        pass

    try:
        op.create_index("ix_purchases_deleted_at", "purchases", ["deleted_at"])
    except Exception:
        pass

    # ── subscriptions table indexes ──────────────────────────────────────────

    try:
        op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    except Exception:
        pass

    try:
        op.create_index("ix_subscriptions_deleted_at", "subscriptions", ["deleted_at"])
    except Exception:
        pass

    try:
        op.create_index(
            "ix_subscriptions_user_status",
            "subscriptions",
            ["user_id", "status"],
        )
    except Exception:
        pass

    # ── api_key_usage table indexes (audit/analytics queries) ────────────────

    try:
        op.create_index("ix_api_key_usage_endpoint", "api_key_usage", ["endpoint"])
    except Exception:
        pass

    try:
        op.create_index(
            "ix_api_key_usage_user_endpoint_ts",
            "api_key_usage",
            ["user_id", "endpoint", "timestamp"],
        )
    except Exception:
        pass

    # ── api_key_rotation table indexes ──────────────────────────────────────

    try:
        op.create_index(
            "ix_api_key_rotation_user_created",
            "api_key_rotation",
            ["user_id", "created_at"],
        )
    except Exception:
        pass

    # ── audit_log table indexes (compliance queries) ─────────────────────────

    try:
        op.create_index("ix_audit_log_client_ip", "audit_log", ["client_ip"])
    except Exception:
        pass

    try:
        op.create_index(
            "ix_audit_log_event_ts",
            "audit_log",
            ["event_type", "timestamp"],
        )
    except Exception:
        pass

    # ── login_attempts table indexes (IP-based analytics) ──────────────────

    try:
        op.create_index(
            "ix_login_attempts_user_created",
            "login_attempts",
            ["user_id", "attempted_at"],
        )
    except Exception:
        pass

    try:
        op.create_index(
            "ix_login_attempts_ip_success",
            "login_attempts",
            ["client_ip", "success", "attempted_at"],
        )
    except Exception:
        pass


def downgrade() -> None:
    """Drop production indexes."""
    conn = op.get_bind()

    # Drop in reverse order of creation
    try:
        op.drop_index("ix_login_attempts_ip_success")
    except Exception:
        pass

    try:
        op.drop_index("ix_login_attempts_user_created")
    except Exception:
        pass

    try:
        op.drop_index("ix_audit_log_event_ts")
    except Exception:
        pass

    try:
        op.drop_index("ix_audit_log_client_ip")
    except Exception:
        pass

    try:
        op.drop_index("ix_api_key_rotation_user_created")
    except Exception:
        pass

    try:
        op.drop_index("ix_api_key_usage_user_endpoint_ts")
    except Exception:
        pass

    try:
        op.drop_index("ix_api_key_usage_endpoint")
    except Exception:
        pass

    try:
        op.drop_index("ix_subscriptions_user_status")
    except Exception:
        pass

    try:
        op.drop_index("ix_subscriptions_deleted_at")
    except Exception:
        pass

    try:
        op.drop_index("ix_subscriptions_status")
    except Exception:
        pass

    try:
        op.drop_index("ix_purchases_deleted_at")
    except Exception:
        pass

    try:
        op.drop_index("ix_purchases_user_persona")
    except Exception:
        pass

    try:
        op.drop_index("ix_purchases_persona_id")
    except Exception:
        pass

    try:
        op.drop_index("ix_users_deleted_at")
    except Exception:
        pass
