"""Initial schema creation

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-04

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. user_preferences
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('dietary_type', sa.String(length=100), nullable=False),
        sa.Column('weekly_budget', sa.Float(), nullable=False),
        sa.Column('household_size', sa.Integer(), nullable=False),
        sa.Column('disliked_ingredients', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # 3. recipes
    op.create_table(
        'recipes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('cuisine', sa.String(length=100), nullable=False),
        sa.Column('dietary_type', sa.String(length=100), nullable=False),
        sa.Column('preparation_minutes', sa.Integer(), nullable=False),
        sa.Column('cooking_minutes', sa.Integer(), nullable=False),
        sa.Column('servings', sa.Integer(), nullable=False),
        sa.Column('instructions', sa.JSON(), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('average_rating', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recipes_cuisine'), 'recipes', ['cuisine'], unique=False)
    op.create_index(op.f('ix_recipes_dietary_type'), 'recipes', ['dietary_type'], unique=False)
    op.create_index(op.f('ix_recipes_name'), 'recipes', ['name'], unique=False)

    # 4. ingredients
    op.create_table(
        'ingredients',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('canonical_name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('default_unit', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ingredients_canonical_name'), 'ingredients', ['canonical_name'], unique=True)
    op.create_index(op.f('ix_ingredients_category'), 'ingredients', ['category'], unique=False)

    # 5. recipe_ingredients
    op.create_table(
        'recipe_ingredients',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('recipe_id', sa.String(length=36), nullable=False),
        sa.Column('ingredient_id', sa.String(length=36), nullable=False),
        sa.Column('raw_text', sa.String(length=500), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column('preparation_note', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. grocery_stores
    op.create_table(
        'grocery_stores',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('store_type', sa.String(length=100), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('is_demo_store', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_grocery_stores_name'), 'grocery_stores', ['name'], unique=True)

    # 7. grocery_products
    op.create_table(
        'grocery_products',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('store_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('brand', sa.String(length=100), nullable=False),
        sa.Column('package_quantity', sa.Float(), nullable=False),
        sa.Column('package_unit', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('in_stock', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['store_id'], ['grocery_stores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_grocery_products_category'), 'grocery_products', ['category'], unique=False)
    op.create_index(op.f('ix_grocery_products_name'), 'grocery_products', ['name'], unique=False)
    op.create_index(op.f('ix_grocery_products_normalized_name'), 'grocery_products', ['normalized_name'], unique=False)
    op.create_index(op.f('ix_grocery_products_store_id'), 'grocery_products', ['store_id'], unique=False)

    # 8. product_prices
    op.create_table(
        'product_prices',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('delivery_fee', sa.Float(), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_source_type', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['grocery_products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_prices_product_id'), 'product_prices', ['product_id'], unique=False)

    # 9. pantry_items
    op.create_table(
        'pantry_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('ingredient_id', sa.String(length=36), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pantry_items_ingredient_id'), 'pantry_items', ['ingredient_id'], unique=False)
    op.create_index(op.f('ix_pantry_items_user_id'), 'pantry_items', ['user_id'], unique=False)

    # 10. recipe_feedbacks
    op.create_table(
        'recipe_feedbacks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('recipe_id', sa.String(length=36), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('difficulty', sa.String(length=50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recipe_feedbacks_recipe_id'), 'recipe_feedbacks', ['recipe_id'], unique=False)
    op.create_index(op.f('ix_recipe_feedbacks_user_id'), 'recipe_feedbacks', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('recipe_feedbacks')
    op.drop_table('pantry_items')
    op.drop_table('product_prices')
    op.drop_table('grocery_products')
    op.drop_table('grocery_stores')
    op.drop_table('recipe_ingredients')
    op.drop_table('ingredients')
    op.drop_table('recipes')
    op.drop_table('user_preferences')
    op.drop_table('users')
