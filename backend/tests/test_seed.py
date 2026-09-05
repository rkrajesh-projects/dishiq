import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.seed import seed_database
from app.models.recipe import Recipe, Ingredient
from app.models.grocery import GroceryStore, GroceryProduct, ProductPrice


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_seed_database_execution_and_counts(db_session):
    seed_database(db_session)

    recipe_count = db_session.query(Recipe).count()
    ingredient_count = db_session.query(Ingredient).count()
    store_count = db_session.query(GroceryStore).count()
    product_count = db_session.query(GroceryProduct).count()
    price_count = db_session.query(ProductPrice).count()

    assert recipe_count >= 15
    assert ingredient_count >= 40
    assert store_count == 3
    assert product_count >= 100
    assert price_count >= 100

    # Verify demo flags
    stores = db_session.query(GroceryStore).all()
    for store in stores:
        assert store.is_demo_store is True

    prices = db_session.query(ProductPrice).all()
    for price in prices:
        assert price.data_source_type == "demo"


def test_seed_database_idempotency(db_session):
    # Run first time
    seed_database(db_session)
    count_run1 = {
        "recipes": db_session.query(Recipe).count(),
        "ingredients": db_session.query(Ingredient).count(),
        "stores": db_session.query(GroceryStore).count(),
        "products": db_session.query(GroceryProduct).count(),
        "prices": db_session.query(ProductPrice).count(),
    }

    # Run second time
    seed_database(db_session)
    count_run2 = {
        "recipes": db_session.query(Recipe).count(),
        "ingredients": db_session.query(Ingredient).count(),
        "stores": db_session.query(GroceryStore).count(),
        "products": db_session.query(GroceryProduct).count(),
        "prices": db_session.query(ProductPrice).count(),
    }

    assert count_run1 == count_run2
