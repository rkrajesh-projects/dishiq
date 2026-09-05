import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.user import User, UserPreference
from app.models.recipe import Recipe, Ingredient, RecipeIngredient
from app.models.grocery import GroceryStore, GroceryProduct, ProductPrice


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_user_and_preference_relationship(db_session):
    user = User(email="test@dishiq.com", hashed_password="password123", full_name="Test User")
    db_session.add(user)
    db_session.commit()

    pref = UserPreference(user_id=user.id, dietary_type="Vegetarian", weekly_budget=200.0)
    db_session.add(pref)
    db_session.commit()

    retrieved_user = db_session.query(User).filter_by(email="test@dishiq.com").first()
    assert retrieved_user is not None
    assert retrieved_user.preference.dietary_type == "Vegetarian"
    assert retrieved_user.preference.weekly_budget == 200.0


def test_recipe_and_ingredient_relationship(db_session):
    ing = Ingredient(canonical_name="paneer", category="Dairy", default_unit="grams")
    db_session.add(ing)
    db_session.commit()

    recipe = Recipe(
        name="Paneer Tikka",
        description="Grilled spiced paneer",
        cuisine="Indian",
        dietary_type="Vegetarian",
        instructions=["Cube paneer", "Marinate and grill"]
    )
    db_session.add(recipe)
    db_session.commit()

    rec_ing = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ing.id,
        raw_text="200g paneer cubes",
        quantity=200.0,
        unit="grams"
    )
    db_session.add(rec_ing)
    db_session.commit()

    retrieved_recipe = db_session.query(Recipe).filter_by(name="Paneer Tikka").first()
    assert len(retrieved_recipe.ingredients) == 1
    assert retrieved_recipe.ingredients[0].ingredient.canonical_name == "paneer"


def test_grocery_store_and_price_demo_flags(db_session):
    store = GroceryStore(name="Demo QuickMart", store_type="Supermarket", is_demo_store=True)
    db_session.add(store)
    db_session.commit()

    prod = GroceryProduct(
        store_id=store.id,
        name="Demo QuickMart Fresh Paneer 200g",
        normalized_name="fresh paneer 200g",
        category="Dairy",
        in_stock=True
    )
    db_session.add(prod)
    db_session.commit()

    price = ProductPrice(product_id=prod.id, price=4.99, data_source_type="demo")
    db_session.add(price)
    db_session.commit()

    retrieved_store = db_session.query(GroceryStore).filter_by(name="Demo QuickMart").first()
    assert retrieved_store.is_demo_store is True
    assert retrieved_store.products[0].prices[0].data_source_type == "demo"
    assert retrieved_store.products[0].prices[0].price == 4.99
