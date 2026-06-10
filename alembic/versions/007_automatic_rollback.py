"""Automatic rollback — H94

Revision ID: 007_automatic_rollback
Revises: 006_performance_metrics
Create Date: 2024-06-10 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_automatic_rollback'
down_revision = '006_performance_metrics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create rollback_policies table
    op.create_table(
        'rollback_policies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('error_rate_threshold_percent', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('latency_threshold_ms', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('window_minutes', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('min_samples', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('require_approval', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('max_rollbacks_per_hour', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create rollback_history table
    op.create_table(
        'rollback_history',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('from_version', sa.String(128), nullable=False),
        sa.Column('to_version', sa.String(128), nullable=False),
        sa.Column('reason', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('initiated_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rollback_history_initiated_at', 'rollback_history', ['initiated_at'])
    op.create_index('ix_rollback_history_status', 'rollback_history', ['status'])
    op.create_index('ix_rollback_history_completed_at', 'rollback_history', ['completed_at'])


def downgrade() -> None:
    op.drop_index('ix_rollback_history_completed_at', table_name='rollback_history')
    op.drop_index('ix_rollback_history_status', table_name='rollback_history')
    op.drop_index('ix_rollback_history_initiated_at', table_name='rollback_history')
    op.drop_table('rollback_history')
    op.drop_table('rollback_policies')
