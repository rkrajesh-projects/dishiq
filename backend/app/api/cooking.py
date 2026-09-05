from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.pantry import get_current_user
from app.services.cooking_session_service import CookingSessionService
from app.schemas.cooking_session import CookingSessionCreate, CookingSessionResponse

router = APIRouter(prefix="/cooking", tags=["Cooking Sessions"])


@router.post("/sessions", response_model=CookingSessionResponse, status_code=status.HTTP_201_CREATED, summary="Start Cooking Session")
def start_cooking_session(body: CookingSessionCreate, db: Session = Depends(get_db)):
    """
    Start a new cooking session for a recipe.
    Uses the default development user context.
    """
    user = get_current_user(db)
    service = CookingSessionService(db)
    return service.create_session(user_id=user.id, payload=body)


from typing import Optional

@router.get("/sessions/active", response_model=Optional[CookingSessionResponse], summary="Get Active Cooking Session")
def get_active_cooking_session(db: Session = Depends(get_db)):
    """
    Retrieve the user's active cooking session, if one exists.
    Uses the default development user context.
    """
    user = get_current_user(db)
    service = CookingSessionService(db)
    return service.get_active_session(user_id=user.id)


@router.get("/sessions/{session_id}", response_model=CookingSessionResponse, summary="Get Cooking Session Details")
def get_cooking_session(session_id: str, db: Session = Depends(get_db)):
    """Retrieve details of an existing cooking session by ID."""
    service = CookingSessionService(db)
    return service.get_session(session_id)


@router.post("/sessions/{session_id}/next", response_model=CookingSessionResponse, summary="Move to Next Step")
def next_cooking_step(session_id: str, db: Session = Depends(get_db)):
    """Move to the next step of the recipe in the cooking session."""
    service = CookingSessionService(db)
    return service.next_step(session_id)


@router.post("/sessions/{session_id}/previous", response_model=CookingSessionResponse, summary="Move to Previous Step")
def previous_cooking_step(session_id: str, db: Session = Depends(get_db)):
    """Move to the previous step of the recipe in the cooking session."""
    service = CookingSessionService(db)
    return service.previous_step(session_id)


@router.post("/sessions/{session_id}/complete", response_model=CookingSessionResponse, summary="Complete Cooking Session")
def complete_cooking_session(session_id: str, db: Session = Depends(get_db)):
    """Mark the cooking session as completed and set completion timestamp."""
    service = CookingSessionService(db)
    return service.complete_session(session_id)
