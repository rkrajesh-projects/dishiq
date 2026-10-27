"""Add servings, updated_at, and prepared_ingredients to cooking_sessions

Revision ID: 006_cooking_session_enhancements
Revises: 005_meal_plans_and_shopping_lists
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '006_cooking_session_enhancements'
down_revision: Union[str, None] = '005_meal_plans_and_shopping_lists'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'cooking_sessions' in existing_tables:
        existing_columns = {col['name'] for col in inspector.get_columns('cooking_sessions')}

        if 'servings' not in existing_columns:
            op.add_column('cooking_sessions', sa.Column('servings', sa.Integer(), nullable=True))

        if 'updated_at' not in existing_columns:
            op.add_column('cooking_sessions', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

        if 'prepared_ingredients' not in existing_columns:
            op.add_column('cooking_sessions', sa.Column('prepared_ingredients', sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'cooking_sessions' in existing_tables:
        existing_columns = {col['name'] for col in inspector.get_columns('cooking_sessions')}

        with op.batch_alter_table('cooking_sessions') as batch_op:
            if 'prepared_ingredients' in existing_columns:
                batch_op.drop_column('prepared_ingredients')
            if 'updated_at' in existing_columns:
                batch_op.drop_column('updated_at')
            if 'servings' in existing_columns:
                batch_op.drop_column('servings')
