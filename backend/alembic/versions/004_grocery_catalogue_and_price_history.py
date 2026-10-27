"""Add source_product_id, currency, price_freshness, and grocery history indexes

Revision ID: 004_grocery_catalogue_and_price_history
Revises: 003_recipe_schema_extension
Create Date: 2026-10-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_grocery_catalogue_and_price_history'
down_revision: Union[str, None] = '003_recipe_schema_extension'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Extend grocery_products table
    existing_gp_cols = {c['name'] for c in inspector.get_columns('grocery_products')}
    with op.batch_alter_table('grocery_products') as batch_op:
        if 'source_product_id' not in existing_gp_cols:
            batch_op.add_column(sa.Column('source_product_id', sa.String(length=255), nullable=True))

    # 2. Extend product_prices table
    existing_pp_cols = {c['name'] for c in inspector.get_columns('product_prices')}
    with op.batch_alter_table('product_prices') as batch_op:
        if 'currency' not in existing_pp_cols:
            batch_op.add_column(sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'))
        if 'price_freshness' not in existing_pp_cols:
            batch_op.add_column(sa.Column('price_freshness', sa.String(length=50), nullable=False, server_default='CACHED'))

    # 3. Add indexes
    existing_gp_indexes = {ix['name'] for ix in inspector.get_indexes('grocery_products')}
    if 'ix_grocery_products_store_source_id' not in existing_gp_indexes:
        op.create_index('ix_grocery_products_store_source_id', 'grocery_products', ['store_id', 'source_product_id'], unique=False)
    if 'ix_grocery_products_store_name_pkg' not in existing_gp_indexes:
        op.create_index('ix_grocery_products_store_name_pkg', 'grocery_products', ['store_id', 'name', 'package_quantity', 'package_unit'], unique=False)

    existing_pp_indexes = {ix['name'] for ix in inspector.get_indexes('product_prices')}
    if 'ix_product_prices_product_observed' not in existing_pp_indexes:
        op.create_index('ix_product_prices_product_observed', 'product_prices', ['product_id', 'observed_at'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_pp_indexes = {ix['name'] for ix in inspector.get_indexes('product_prices')}
    if 'ix_product_prices_product_observed' in existing_pp_indexes:
        op.drop_index('ix_product_prices_product_observed', table_name='product_prices')

    existing_gp_indexes = {ix['name'] for ix in inspector.get_indexes('grocery_products')}
    if 'ix_grocery_products_store_name_pkg' in existing_gp_indexes:
        op.drop_index('ix_grocery_products_store_name_pkg', table_name='grocery_products')
    if 'ix_grocery_products_store_source_id' in existing_gp_indexes:
        op.drop_index('ix_grocery_products_store_source_id', table_name='grocery_products')

    existing_pp_cols = {c['name'] for c in inspector.get_columns('product_prices')}
    with op.batch_alter_table('product_prices') as batch_op:
        if 'price_freshness' in existing_pp_cols:
            batch_op.drop_column('price_freshness')
        if 'currency' in existing_pp_cols:
            batch_op.drop_column('currency')

    existing_gp_cols = {c['name'] for c in inspector.get_columns('grocery_products')}
    with op.batch_alter_table('grocery_products') as batch_op:
        if 'source_product_id' in existing_gp_cols:
            batch_op.drop_column('source_product_id')
