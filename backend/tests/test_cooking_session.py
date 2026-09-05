import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.db.base import Base
from app.models.user import User
from app.models.recipe import Recipe
from app.models.cooking_session import CookingSession
from app.repositories.cooking_session_repository import CookingSessionRepository
from app.services.cooking_session_service import CookingSessionService
from app.schemas.cooking_session import CookingSessionCreate, CookingSessionUpdate
from app.core.exceptions import DishIQException


@pytest.fixture
def db_session():
    """Isolated SQLite in-memory database session for CookingSession tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _create_user_and_recipe(db):
    """Helper to populate a default user and recipe."""
    user = User(email="chef@dishiq.com", hashed_password="password123", full_name="Chef Dave")
    recipe = Recipe(
        name="Paneer Bhurji",
        description="Spiced scrambled cottage cheese",
        cuisine="Indian",
        dietary_type="Vegetarian",
        instructions=["Crumble paneer", "Cook veggies", "Combine"]
    )
    db.add_all([user, recipe])
    db.commit()
    db.refresh(user)
    db.refresh(recipe)
    return user, recipe


# 1. CookingSession creation
# 2. Default current_step
# 3. Default status
# 4. UTC started_at
def test_cooking_session_creation_and_defaults(db_session):
    user, recipe = _create_user_and_recipe(db_session)
    
    session = CookingSession(
        user_id=user.id,
        recipe_id=recipe.id,
        notes="First attempt"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    
    assert session.id is not None
    assert session.current_step == 0
    assert session.status == "active"
    assert session.started_at is not None
    if session.started_at.tzinfo is not None:
        assert session.started_at.tzinfo == timezone.utc
    assert abs((datetime.now(timezone.utc) - session.started_at.replace(tzinfo=timezone.utc)).total_seconds()) < 5
    assert session.completed_at is None
    assert session.notes == "First attempt"


# 5. Recipe foreign-key relationship
# 6. User foreign-key relationship
# 7. User relationship
# 8. Recipe relationship
def test_relationships(db_session):
    user, recipe = _create_user_and_recipe(db_session)
    
    session = CookingSession(
        user_id=user.id,
        recipe_id=recipe.id
    )
    db_session.add(session)
    db_session.commit()
    
    # Verify relationship mappings
    assert session.user.email == "chef@dishiq.com"
    assert session.recipe.name == "Paneer Bhurji"
    
    # Backpopulate tests
    db_session.refresh(user)
    db_session.refresh(recipe)
    assert len(user.cooking_sessions) == 1
    assert len(recipe.cooking_sessions) == 1
    assert user.cooking_sessions[0].id == session.id
    assert recipe.cooking_sessions[0].id == session.id


def test_invalid_foreign_keys(db_session):
    # Missing non-nullable fields raises IntegrityError
    session = CookingSession(notes="No user or recipe")
    db_session.add(session)
    with pytest.raises(IntegrityError):
        db_session.commit()


# 9. Valid active status
# 10. Valid paused status
# 11. Valid completed status
# 12. Invalid status
def test_status_check_constraints(db_session):
    user, recipe = _create_user_and_recipe(db_session)
    
    # Active
    s1 = CookingSession(user_id=user.id, recipe_id=recipe.id, status="active")
    db_session.add(s1)
    
    # Paused
    s2 = CookingSession(user_id=user.id, recipe_id=recipe.id, status="paused")
    db_session.add(s2)
    
    # Completed
    s3 = CookingSession(user_id=user.id, recipe_id=recipe.id, status="completed")
    db_session.add(s3)
    
    db_session.commit()
    
    # Invalid status should violate CheckConstraint
    s4 = CookingSession(user_id=user.id, recipe_id=recipe.id, status="archived")
    db_session.add(s4)
    with pytest.raises(IntegrityError):
        db_session.commit()


# 13. Negative current_step
def test_negative_step_constraint(db_session):
    user, recipe = _create_user_and_recipe(db_session)
    
    s = CookingSession(user_id=user.id, recipe_id=recipe.id, current_step=-5)
    db_session.add(s)
    with pytest.raises(IntegrityError):
        db_session.commit()


# 14. Completion timestamp behavior
def test_completion_timestamp_service_logic(db_session):
    user, recipe = _create_user_and_recipe(db_session)
    service = CookingSessionService(db_session)
    
    # Create active session
    create_payload = CookingSessionCreate(recipe_id=recipe.id, notes="Test completion timing")
    session = service.create_session(user.id, create_payload)
    assert session.status == "active"
    assert session.completed_at is None
    
    # Update to paused
    update_paused = CookingSessionUpdate(status="paused")
    session = service.update_session(session.id, update_paused)
    assert session.status == "paused"
    assert session.completed_at is None
    
    # Transition to completed
    update_completed = CookingSessionUpdate(status="completed")
    session = service.update_session(session.id, update_completed)
    assert session.status == "completed"
    assert session.completed_at is not None
    assert abs((datetime.now(timezone.utc) - session.completed_at.replace(tzinfo=timezone.utc)).total_seconds()) < 5
    
    # Transition back to active clears completed_at
    update_active = CookingSessionUpdate(status="active")
    session = service.update_session(session.id, update_active)
    assert session.status == "active"
    assert session.completed_at is None


# 15. Repository behavior
def test_repository_crud(db_session):
    user, recipe = _create_user_and_recipe(db_session)
    repo = CookingSessionRepository(db_session)
    
    # Create
    session = repo.create(user_id=user.id, recipe_id=recipe.id, notes="Repo test notes")
    assert session.id is not None
    
    # Get by ID
    fetched = repo.get_by_id(session.id)
    assert fetched.id == session.id
    assert fetched.notes == "Repo test notes"
    
    # List for user
    sessions_list = repo.list_for_user(user.id)
    assert len(sessions_list) == 1
    assert sessions_list[0].id == session.id
    
    # Save (update)
    fetched.notes = "Updated notes"
    repo.save(fetched)
    
    db_session.expire_all()
    updated = repo.get_by_id(session.id)
    assert updated.notes == "Updated notes"


# 16. Service validation
def test_service_validations_and_errors(db_session):
    user, recipe = _create_user_and_recipe(db_session)
    service = CookingSessionService(db_session)
    
    # Create invalid user raises exception
    with pytest.raises(DishIQException) as exc:
        service.create_session("nonexistent-user-uuid", CookingSessionCreate(recipe_id=recipe.id))
    assert exc.value.status_code == 404
    assert exc.value.code == "USER_NOT_FOUND"
    
    # Create invalid recipe raises exception
    with pytest.raises(DishIQException) as exc:
        service.create_session(user.id, CookingSessionCreate(recipe_id="nonexistent-recipe-uuid"))
    assert exc.value.status_code == 404
    assert exc.value.code == "RECIPE_NOT_FOUND"

    # Create valid session
    session = service.create_session(user.id, CookingSessionCreate(recipe_id=recipe.id))
    # Update invalid step
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        CookingSessionUpdate(current_step=-2)
    
    # Update invalid status
    with pytest.raises(ValidationError):
        CookingSessionUpdate(status="invalid_status")
