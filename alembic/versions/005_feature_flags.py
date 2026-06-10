"""Feature flags (A/B testing) — H92

Revision ID: 005_feature_flags
Revises: 004_payment_billing
Create Date: 2024-06-10 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_feature_flags'
down_revision = '004_payment_billing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create feature_flags table
    op.create_table(
        'feature_flags',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('rollout_percentage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('variants', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('targeted_user_ids', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('target_segments', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('target_tiers', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_feature_flags_name_enabled', 'feature_flags', ['name', 'enabled'])
    op.create_index('ix_feature_flags_name', 'feature_flags', ['name'], unique=True)
    op.create_index('ix_feature_flags_enabled', 'feature_flags', ['enabled'])
    op.create_index('ix_feature_flags_expires_at', 'feature_flags', ['expires_at'])

    # Create flag_evaluations table
    op.create_table(
        'flag_evaluations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('flag_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('variant', sa.String(64), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['flag_id'], ['feature_flags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_flag_evaluations_flag_user', 'flag_evaluations', ['flag_id', 'user_id'])
    op.create_index('ix_flag_evaluations_evaluated_at', 'flag_evaluations', ['evaluated_at'])
    op.create_index('ix_flag_evaluations_flag_id', 'flag_evaluations', ['flag_id'])
    op.create_index('ix_flag_evaluations_user_id', 'flag_evaluations', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_flag_evaluations_user_id', table_name='flag_evaluations')
    op.drop_index('ix_flag_evaluations_flag_id', table_name='flag_evaluations')
    op.drop_index('ix_flag_evaluations_evaluated_at', table_name='flag_evaluations')
    op.drop_index('ix_flag_evaluations_flag_user', table_name='flag_evaluations')
    op.drop_table('flag_evaluations')

    op.drop_index('ix_feature_flags_expires_at', table_name='feature_flags')
    op.drop_index('ix_feature_flags_enabled', table_name='feature_flags')
    op.drop_index('ix_feature_flags_name', table_name='feature_flags')
    op.drop_index('ix_feature_flags_name_enabled', table_name='feature_flags')
    op.drop_table('feature_flags')
