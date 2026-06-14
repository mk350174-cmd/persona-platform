"""HPEP-100 Quiz — Persona Extraction Protocol tables

Revision ID: 008_hpep100_quiz
Revises: 007_automatic_rollback
Create Date: 2026-06-14 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_hpep100_quiz'
down_revision = '007_automatic_rollback'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create quiz_submissions table
    op.create_table(
        'quiz_submissions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('k_layer', sa.JSON(), nullable=False),
        sa.Column('ceid_scores', sa.JSON(), nullable=False),
        sa.Column('tier', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quiz_submissions_user_created', 'quiz_submissions', ['user_id', 'created_at'])
    op.create_index('ix_quiz_submissions_user_id', 'quiz_submissions', ['user_id'])

    # Create user_personas table
    op.create_table(
        'user_personas',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('k_layer', sa.JSON(), nullable=False),
        sa.Column('ceid_scores', sa.JSON(), nullable=False),
        sa.Column('tier', sa.String(32), nullable=True),
        sa.Column('submission_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['quiz_submissions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_user_personas_user_id', 'user_personas', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_user_personas_user_id', table_name='user_personas')
    op.drop_table('user_personas')

    op.drop_index('ix_quiz_submissions_user_id', table_name='quiz_submissions')
    op.drop_index('ix_quiz_submissions_user_created', table_name='quiz_submissions')
    op.drop_table('quiz_submissions')
