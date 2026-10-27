"""Create meal_plans, meal_plan_items, shopping_lists, and shopping_list_items tables

Revision ID: 005_meal_plans_and_shopping_lists
Revises: 004_grocery_catalogue_and_price_history
Create Date: 2026-10-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_meal_plans_and_shopping_lists'
down_revision: Union[str, None] = '004_grocery_catalogue_and_price_history'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. meal_plans table
    if 'meal_plans' not in existing_tables:
        op.create_table(
            'meal_plans',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('start_date', sa.Date(), nullable=True),
            sa.Column('end_date', sa.Date(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_meal_plans_user_id', 'meal_plans', ['user_id'], unique=False)

    # 2. meal_plan_items table
    if 'meal_plan_items' not in existing_tables:
        op.create_table(
            'meal_plan_items',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('meal_plan_id', sa.String(length=36), sa.ForeignKey('meal_plans.id', ondelete='CASCADE'), nullable=False),
            sa.Column('recipe_id', sa.String(length=36), sa.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('meal_date', sa.Date(), nullable=True),
            sa.Column('meal_type', sa.String(length=50), nullable=False, server_default='dinner'),
            sa.Column('servings', sa.Integer(), nullable=False, server_default='2'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint('servings > 0', name='chk_meal_plan_item_servings_positive'),
        )
        op.create_index('ix_meal_plan_items_meal_plan_id', 'meal_plan_items', ['meal_plan_id'], unique=False)
        op.create_index('ix_meal_plan_items_recipe_id', 'meal_plan_items', ['recipe_id'], unique=False)

    # 3. shopping_lists table
    if 'shopping_lists' not in existing_tables:
        op.create_table(
            'shopping_lists',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
            sa.Column('meal_plan_id', sa.String(length=36), sa.ForeignKey('meal_plans.id', ondelete='SET NULL'), nullable=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_shopping_lists_user_id', 'shopping_lists', ['user_id'], unique=False)
        op.create_index('ix_shopping_lists_meal_plan_id', 'shopping_lists', ['meal_plan_id'], unique=False)

    # 4. shopping_list_items table
    if 'shopping_list_items' not in existing_tables:
        op.create_table(
            'shopping_list_items',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('shopping_list_id', sa.String(length=36), sa.ForeignKey('shopping_lists.id', ondelete='CASCADE'), nullable=False),
            sa.Column('ingredient_id', sa.String(length=36), sa.ForeignKey('ingredients.id', ondelete='SET NULL'), nullable=True),
            sa.Column('ingredient_name', sa.String(length=255), nullable=False),
            sa.Column('required_quantity', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('unit', sa.String(length=50), nullable=False, server_default='piece'),
            sa.Column('pantry_quantity', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('quantity_to_buy', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('user_quantity_override', sa.Float(), nullable=True),
            sa.Column('is_obtained', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_manual', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('source_recipes', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint('required_quantity >= 0', name='chk_sli_required_quantity_non_negative'),
            sa.CheckConstraint('quantity_to_buy >= 0', name='chk_sli_quantity_to_buy_non_negative'),
        )
        op.create_index('ix_shopping_list_items_shopping_list_id', 'shopping_list_items', ['shopping_list_id'], unique=False)
        op.create_index('ix_shopping_list_items_ingredient_id', 'shopping_list_items', ['ingredient_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'shopping_list_items' in existing_tables:
        op.drop_table('shopping_list_items')
    if 'shopping_lists' in existing_tables:
        op.drop_table('shopping_lists')
    if 'meal_plan_items' in existing_tables:
        op.drop_table('meal_plan_items')
    if 'meal_plans' in existing_tables:
        op.drop_table('meal_plans')
