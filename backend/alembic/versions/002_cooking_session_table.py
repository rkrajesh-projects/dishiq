"""Create cooking session table

Revision ID: 002_cooking_session_table
Revises: 001_initial_schema
Create Date: 2026-08-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_cooking_session_table'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cooking_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('recipe_id', sa.String(length=36), nullable=False),
        sa.Column('current_step', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.CheckConstraint('current_step >= 0', name='chk_cooking_session_current_step_non_negative'),
        sa.CheckConstraint("status IN ('active', 'paused', 'completed')", name='chk_cooking_session_status_valid'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cooking_sessions_recipe_id'), 'cooking_sessions', ['recipe_id'], unique=False)
    op.create_index(op.f('ix_cooking_sessions_user_id'), 'cooking_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cooking_sessions_user_id'), table_name='cooking_sessions')
    op.drop_index(op.f('ix_cooking_sessions_recipe_id'), table_name='cooking_sessions')
    op.drop_table('cooking_sessions')
