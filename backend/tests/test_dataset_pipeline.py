import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.services.dataset_pipeline import DatasetPipeline, ImportedRecipe, NormalizedIngredient, Provenance
from app.models.recipe import Recipe

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_pipeline_validation():
    pipeline = DatasetPipeline(None)
    
    # Valid recipe
    valid_rec = ImportedRecipe(
        name="Test Recipe",
        cuisine="Indian",
        dietary_type="Vegetarian",
        ingredients=[NormalizedIngredient(raw_text="1 cup water", canonical_name="water", quantity=1, unit="cup")],
        instructions=["Boil water"],
        provenance=Provenance(source_name="TestSource", dataset_version="v1")
    )
    assert pipeline.validate_recipe(valid_rec) == True
    
    # Missing name
    invalid_rec = valid_rec.copy(update={"name": ""})
    assert pipeline.validate_recipe(invalid_rec) == False

def test_pipeline_import_and_dedup(db_session):
    pipeline = DatasetPipeline(db_session)
    rec1 = ImportedRecipe(
        name="Sambar",
        cuisine="South Indian",
        dietary_type="Vegetarian",
        ingredients=[NormalizedIngredient(raw_text="Toor Dal", canonical_name="toor dal", quantity=1, unit="cup")],
        instructions=["Cook dal"],
        provenance=Provenance(source_name="Test", source_recipe_id="test1", dataset_version="v1", verification_status="VERIFIED")
    )
    
    # Import first time
    manifest1 = pipeline.process_import([rec1], "v1")
    assert manifest1["valid_records"] == 1
    assert manifest1["duplicates"] == 0
    assert manifest1["verified_records"] == 1
    
    # Verify in DB
    db_rec = db_session.query(Recipe).filter_by(source_recipe_id="test1").first()
    assert db_rec is not None
    assert db_rec.verification_status == "VERIFIED"
    assert db_rec.is_indian_recipe == True
    
    # Import second time (deduplication)
    pipeline = DatasetPipeline(db_session) # new pipeline instance
    manifest2 = pipeline.process_import([rec1], "v1")
    assert manifest2["valid_records"] == 0
    assert manifest2["duplicates"] == 1

def test_ingredient_normalization():
    pipeline = DatasetPipeline(None)
    assert pipeline._normalize_ingredient_name("Dhaniya") == "coriander leaves"
    assert pipeline._normalize_ingredient_name("  TOMATOES  ") == "tomato"
    assert pipeline._normalize_ingredient_name("Salt") == "salt"
