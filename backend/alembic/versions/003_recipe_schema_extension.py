"""Add extended recipe metadata columns and indexes

Revision ID: 003_recipe_schema_extension
Revises: 002_cooking_session_table
Create Date: 2026-10-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_recipe_schema_extension'
down_revision: Union[str, None] = '002_cooking_session_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # 1. Extend recipes table if columns missing
    existing_recipe_cols = {c['name'] for c in inspector.get_columns('recipes')}
    
    columns_to_add = [
        ('source_recipe_id', sa.Column('source_recipe_id', sa.String(length=255), nullable=True)),
        ('source_license', sa.Column('source_license', sa.String(length=255), nullable=True)),
        ('author', sa.Column('author', sa.String(length=255), nullable=True)),
        ('verification_status', sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='UNVERIFIED')),
        ('verification_level', sa.Column('verification_level', sa.String(length=50), nullable=False, server_default='NONE')),
        ('dataset_version', sa.Column('dataset_version', sa.String(length=100), nullable=True)),
        ('region', sa.Column('region', sa.String(length=100), nullable=True)),
        ('state', sa.Column('state', sa.String(length=100), nullable=True)),
        ('original_name', sa.Column('original_name', sa.String(length=255), nullable=True)),
        ('original_language', sa.Column('original_language', sa.String(length=100), nullable=True)),
        ('is_indian_recipe', sa.Column('is_indian_recipe', sa.Boolean(), nullable=False, server_default='0')),
        ('collected_at', sa.Column('collected_at', sa.DateTime(timezone=True), nullable=True)),
    ]
    
    with op.batch_alter_table('recipes') as batch_op:
        for col_name, col_obj in columns_to_add:
            if col_name not in existing_recipe_cols:
                batch_op.add_column(col_obj)

    # 2. Add indexes
    existing_recipe_indexes = {ix['name'] for ix in inspector.get_indexes('recipes')}
    if 'ix_recipes_source_recipe_id' not in existing_recipe_indexes:
        op.create_index(op.f('ix_recipes_source_recipe_id'), 'recipes', ['source_recipe_id'], unique=False)

    existing_ri_indexes = {ix['name'] for ix in inspector.get_indexes('recipe_ingredients')}
    if 'ix_recipe_ingredients_recipe_id' not in existing_ri_indexes:
        op.create_index(op.f('ix_recipe_ingredients_recipe_id'), 'recipe_ingredients', ['recipe_id'], unique=False)
    if 'ix_recipe_ingredients_ingredient_id' not in existing_ri_indexes:
        op.create_index(op.f('ix_recipe_ingredients_ingredient_id'), 'recipe_ingredients', ['ingredient_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Drop indexes
    ri_indexes = {ix['name'] for ix in inspector.get_indexes('recipe_ingredients')}
    if 'ix_recipe_ingredients_ingredient_id' in ri_indexes:
        op.drop_index(op.f('ix_recipe_ingredients_ingredient_id'), table_name='recipe_ingredients')
    if 'ix_recipe_ingredients_recipe_id' in ri_indexes:
        op.drop_index(op.f('ix_recipe_ingredients_recipe_id'), table_name='recipe_ingredients')

    recipe_indexes = {ix['name'] for ix in inspector.get_indexes('recipes')}
    if 'ix_recipes_source_recipe_id' in recipe_indexes:
        op.drop_index(op.f('ix_recipes_source_recipe_id'), table_name='recipes')

    # Drop columns
    with op.batch_alter_table('recipes') as batch_op:
        batch_op.drop_column('collected_at')
        batch_op.drop_column('is_indian_recipe')
        batch_op.drop_column('original_language')
        batch_op.drop_column('original_name')
        batch_op.drop_column('state')
        batch_op.drop_column('region')
        batch_op.drop_column('dataset_version')
        batch_op.drop_column('verification_level')
        batch_op.drop_column('verification_status')
        batch_op.drop_column('author')
        batch_op.drop_column('source_license')
        batch_op.drop_column('source_recipe_id')
