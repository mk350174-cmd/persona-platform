"""Performance metrics & regression detection — H93

Revision ID: 006_performance_metrics
Revises: 005_feature_flags
Create Date: 2024-06-10 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_performance_metrics'
down_revision = '005_feature_flags'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create performance_metrics table
    op.create_table(
        'performance_metrics',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('metric_type', sa.String(64), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.String(256), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_performance_metrics_type_endpoint', 'performance_metrics', ['metric_type', 'endpoint'])
    op.create_index('ix_performance_metrics_metric_type', 'performance_metrics', ['metric_type'])
    op.create_index('ix_performance_metrics_endpoint', 'performance_metrics', ['endpoint'])
    op.create_index('ix_performance_metrics_recorded_at', 'performance_metrics', ['recorded_at'])

    # Create performance_baselines table
    op.create_table(
        'performance_baselines',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('metric_type', sa.String(64), nullable=False),
        sa.Column('endpoint', sa.String(256), nullable=True),
        sa.Column('p50', sa.Integer(), nullable=False),
        sa.Column('p95', sa.Integer(), nullable=False),
        sa.Column('p99', sa.Integer(), nullable=False),
        sa.Column('mean', sa.Integer(), nullable=False),
        sa.Column('stddev', sa.Integer(), nullable=False),
        sa.Column('min_val', sa.Integer(), nullable=False),
        sa.Column('max_val', sa.Integer(), nullable=False),
        sa.Column('sample_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_performance_baselines_type_endpoint', 'performance_baselines', ['metric_type', 'endpoint'])
    op.create_index('ix_performance_baselines_metric_type', 'performance_baselines', ['metric_type'])
    op.create_index('ix_performance_baselines_created_at', 'performance_baselines', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_performance_baselines_created_at', table_name='performance_baselines')
    op.drop_index('ix_performance_baselines_metric_type', table_name='performance_baselines')
    op.drop_index('ix_performance_baselines_type_endpoint', table_name='performance_baselines')
    op.drop_table('performance_baselines')

    op.drop_index('ix_performance_metrics_recorded_at', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_endpoint', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_metric_type', table_name='performance_metrics')
    op.drop_index('ix_performance_metrics_type_endpoint', table_name='performance_metrics')
    op.drop_table('performance_metrics')
