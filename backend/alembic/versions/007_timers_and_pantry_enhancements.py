"""Add cooking_timers, pantry_items extensions, and pantry_consumption_logs

Revision ID: 007_timers_and_pantry_enhancements
Revises: 006_cooking_session_enhancements
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '007_timers_and_pantry_enhancements'
down_revision: Union[str, None] = '006_cooking_session_enhancements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Create cooking_timers if not exists
    if 'cooking_timers' not in existing_tables:
        op.create_table(
            'cooking_timers',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('cooking_session_id', sa.String(length=36), sa.ForeignKey('cooking_sessions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('recipe_id', sa.String(length=36), sa.ForeignKey('recipes.id', ondelete='SET NULL'), nullable=True),
            sa.Column('step_index', sa.Integer(), nullable=True),
            sa.Column('label', sa.String(length=255), nullable=False),
            sa.Column('duration_seconds', sa.Integer(), nullable=False),
            sa.Column('remaining_seconds', sa.Float(), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='idle'),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint('duration_seconds > 0 AND duration_seconds <= 86400', name='chk_cooking_timer_duration_valid'),
            sa.CheckConstraint('remaining_seconds >= 0', name='chk_cooking_timer_remaining_non_negative'),
            sa.CheckConstraint("status IN ('idle', 'running', 'paused', 'completed', 'cancelled')", name='chk_cooking_timer_status_valid'),
        )
        op.create_index('ix_cooking_timers_user_id', 'cooking_timers', ['user_id'])
        op.create_index('ix_cooking_timers_cooking_session_id', 'cooking_timers', ['cooking_session_id'])
        op.create_index('ix_cooking_timers_recipe_id', 'cooking_timers', ['recipe_id'])

    # 2. Add columns to pantry_items if not present
    if 'pantry_items' in existing_tables:
        pantry_cols = {col['name'] for col in inspector.get_columns('pantry_items')}
        if 'custom_name' not in pantry_cols:
            op.add_column('pantry_items', sa.Column('custom_name', sa.String(length=255), nullable=True))
        if 'location' not in pantry_cols:
            op.add_column('pantry_items', sa.Column('location', sa.String(length=100), nullable=True))
        if 'notes' not in pantry_cols:
            op.add_column('pantry_items', sa.Column('notes', sa.Text(), nullable=True))

    # 3. Create pantry_consumption_logs if not exists
    if 'pantry_consumption_logs' not in existing_tables:
        op.create_table(
            'pantry_consumption_logs',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('token', sa.String(length=64), nullable=False),
            sa.Column('recipe_id', sa.String(length=36), sa.ForeignKey('recipes.id', ondelete='SET NULL'), nullable=True),
            sa.Column('cooking_session_id', sa.String(length=36), sa.ForeignKey('cooking_sessions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('items', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_pantry_consumption_logs_user_id', 'pantry_consumption_logs', ['user_id'])
        op.create_index('ix_pantry_consumption_logs_token', 'pantry_consumption_logs', ['token'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'pantry_consumption_logs' in existing_tables:
        op.drop_table('pantry_consumption_logs')

    if 'pantry_items' in existing_tables:
        pantry_cols = {col['name'] for col in inspector.get_columns('pantry_items')}
        with op.batch_alter_table('pantry_items') as batch_op:
            if 'notes' in pantry_cols:
                batch_op.drop_column('notes')
            if 'location' in pantry_cols:
                batch_op.drop_column('location')
            if 'custom_name' in pantry_cols:
                batch_op.drop_column('custom_name')

    if 'cooking_timers' in existing_tables:
        op.drop_table('cooking_timers')
