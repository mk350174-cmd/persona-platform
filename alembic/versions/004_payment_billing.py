"""payment_billing — Invoice, Wallet, Referral, and Promo tables for B13-B24

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-10 14:00:00.000000
"""

from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    # ── 1. Add stripe_customer_id and subscription fields to users ───────────────

    if is_sqlite:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("stripe_customer_id", sa.String(128), nullable=True, unique=True, index=True))
    else:
        op.add_column("users", sa.Column("stripe_customer_id", sa.String(128), nullable=True, unique=True, index=True))

    # ── 2. invoices table ────────────────────────────────────────────────────────

    op.create_table(
        "invoices",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("stripe_invoice_id", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("amount_usd_cents", sa.Integer(), nullable=False),  # in cents
        sa.Column("status", sa.String(16), nullable=False, server_default="draft", index=True),  # draft, open, paid, void
        sa.Column("issued_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("pdf_url", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # ── 3. wallets table ─────────────────────────────────────────────────────────

    op.create_table(
        "wallets",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("balance_cents", sa.Integer(), nullable=False, server_default="0"),  # in cents
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # ── 4. referral_codes table ──────────────────────────────────────────────────

    op.create_table(
        "referral_codes",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("referrer_id", sa.String(36), nullable=False, index=True),
        sa.Column("code", sa.String(16), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["referrer_id"], ["users.id"], ondelete="CASCADE"),
    )

    # ── 5. referral_credits table ────────────────────────────────────────────────

    op.create_table(
        "referral_credits",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column("referrer_id", sa.String(36), nullable=False, index=True),
        sa.Column("referee_id", sa.String(36), nullable=False, index=True),
        sa.Column("credit_amount_cents", sa.Integer(), nullable=False),  # e.g., 500 = $5
        sa.Column("status", sa.String(16), nullable=False, server_default="pending", index=True),  # pending, issued, used
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["referrer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referee_id"], ["users.id"], ondelete="CASCADE"),
    )

    # ── 6. promo_codes table (optional: can also use Stripe API directly) ────────

    op.create_table(
        "promo_codes",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("stripe_promotion_id", sa.String(128), nullable=True, unique=True),
        sa.Column("discount_percent", sa.Integer(), nullable=False),  # 0-100
        sa.Column("status", sa.String(16), nullable=False, server_default="active", index=True),  # active, expired, disabled
        sa.Column("expires_at", sa.DateTime(), nullable=True, index=True),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),  # None = unlimited
        sa.Column("redemption_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
    )

    # ── 7. Add subscription_tier to subscriptions table ──────────────────────────

    if is_sqlite:
        with op.batch_alter_table("subscriptions") as batch_op:
            batch_op.add_column(sa.Column("billing_period", sa.String(16), nullable=True, server_default="month"))  # month, year
    else:
        op.add_column("subscriptions", sa.Column("billing_period", sa.String(16), nullable=True, server_default="month"))


def downgrade() -> None:
    # Drop tables in reverse order of dependencies
    op.drop_table("promo_codes")
    op.drop_table("referral_credits")
    op.drop_table("referral_codes")
    op.drop_table("wallets")
    op.drop_table("invoices")

    # Drop columns from subscriptions
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("subscriptions") as batch_op:
            batch_op.drop_column("billing_period")
    else:
        op.drop_column("subscriptions", "billing_period")

    # Drop stripe_customer_id from users
    if is_sqlite:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("stripe_customer_id")
    else:
        op.drop_constraint("uq_users_stripe_customer_id", "users", type_="unique")
        op.drop_column("users", "stripe_customer_id")
