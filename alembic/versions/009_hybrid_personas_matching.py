"""Hybrid persona integration — Phase 2-3 (Database schema + matching audit)

Revision ID: 009_hybrid_personas_matching
Revises: 008_hpep100_quiz
Create Date: 2026-06-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_hybrid_personas_matching'
down_revision = '008_hpep100_quiz'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create hybrid_personas table
    op.create_table(
        'hybrid_personas',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('persona_id', sa.String(64), nullable=False),
        sa.Column('combination_number', sa.Integer(), nullable=False),
        sa.Column('name_tr', sa.String(255), nullable=False),
        sa.Column('name_en', sa.String(255), nullable=False),
        sa.Column('active_k_layers', sa.JSON(), nullable=False),
        sa.Column('suppressed_k_layers', sa.JSON(), nullable=False),
        sa.Column('use_case', sa.String(1000), nullable=False),
        sa.Column('characteristic', sa.String(2000), nullable=False),
        sa.Column('example_outputs', sa.String(2000), nullable=True),
        sa.Column('price_usd', sa.Integer(), nullable=True),
        sa.Column('is_available', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_hybrid_personas_number', 'hybrid_personas', ['combination_number'], unique=True)
    op.create_index('ix_hybrid_personas_available', 'hybrid_personas', ['is_available'])
    op.create_index('ix_hybrid_personas_created', 'hybrid_personas', ['created_at'])
    op.create_index('ix_hybrid_personas_persona_id', 'hybrid_personas', ['persona_id'], unique=True)

    # Create persona_matches table
    op.create_table(
        'persona_matches',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('submission_id', sa.String(36), nullable=False),
        sa.Column('top_persona_id', sa.String(64), nullable=False),
        sa.Column('is_historical', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('match_score', sa.Integer(), nullable=False),
        sa.Column('top_5_persona_ids', sa.JSON(), nullable=False),
        sa.Column('top_5_scores', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['quiz_submissions.id'], ),
        sa.ForeignKeyConstraint(['top_persona_id'], ['hybrid_personas.persona_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_persona_matches_user_created', 'persona_matches', ['user_id', 'created_at'])
    op.create_index('ix_persona_matches_submission_id', 'persona_matches', ['submission_id'])
    op.create_index('ix_persona_matches_top_persona', 'persona_matches', ['top_persona_id'])
    op.create_index('ix_persona_matches_user_id', 'persona_matches', ['user_id'])

    # Add columns to quiz_submissions for hybrid matching
    op.add_column('quiz_submissions',
        sa.Column('matched_hybrid_persona_id', sa.String(64), nullable=True)
    )
    op.add_column('quiz_submissions',
        sa.Column('hybrid_match_score', sa.Integer(), nullable=True)
    )
    op.add_column('quiz_submissions',
        sa.Column('top_5_hybrid_matches', sa.JSON(), nullable=True)
    )
    op.add_column('quiz_submissions',
        sa.Column('top_5_hybrid_scores', sa.JSON(), nullable=True)
    )
    op.create_foreign_key(
        'fk_quiz_submissions_hybrid_persona',
        'quiz_submissions',
        'hybrid_personas',
        ['matched_hybrid_persona_id'],
        ['persona_id']
    )


def downgrade() -> None:
    # Drop foreign key constraint from quiz_submissions
    op.drop_constraint('fk_quiz_submissions_hybrid_persona', 'quiz_submissions', type_='foreignkey')

    # Drop columns from quiz_submissions
    op.drop_column('quiz_submissions', 'top_5_hybrid_scores')
    op.drop_column('quiz_submissions', 'top_5_hybrid_matches')
    op.drop_column('quiz_submissions', 'hybrid_match_score')
    op.drop_column('quiz_submissions', 'matched_hybrid_persona_id')

    # Drop persona_matches table
    op.drop_index('ix_persona_matches_user_id', 'persona_matches')
    op.drop_index('ix_persona_matches_top_persona', 'persona_matches')
    op.drop_index('ix_persona_matches_submission_id', 'persona_matches')
    op.drop_index('ix_persona_matches_user_created', 'persona_matches')
    op.drop_table('persona_matches')

    # Drop hybrid_personas table
    op.drop_index('ix_hybrid_personas_persona_id', 'hybrid_personas')
    op.drop_index('ix_hybrid_personas_created', 'hybrid_personas')
    op.drop_index('ix_hybrid_personas_available', 'hybrid_personas')
    op.drop_index('ix_hybrid_personas_number', 'hybrid_personas')
    op.drop_table('hybrid_personas')
