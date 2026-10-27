from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.cooking_session_service import CookingSessionService
from app.services.cooking_timer_service import CookingTimerService
from app.services.cooking_companion_service import CookingCompanionService
from app.schemas.cooking_session import (
    CookingSessionCreate,
    CookingSessionUpdate,
    CookingSessionResponse,
    PreparedIngredientsUpdate,
    PreparationChecklistResponse,
)
from app.schemas.cooking_timer import (
    CookingTimerCreate,
    CookingTimerResponse,
)
from app.schemas.cooking_companion import (
    CompanionChatRequest,
    CompanionChatResponse,
)

router = APIRouter(prefix="/cooking", tags=["Cooking Sessions"])


@router.post(
    "/sessions",
    response_model=CookingSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Cooking Session",
)
def start_cooking_session(
    body: CookingSessionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Start a new cooking session for a recipe with specified servings.
    """
    service = CookingSessionService(db)
    return service.create_session(user_id=user.id, payload=body)


@router.get(
    "/sessions/active",
    response_model=Optional[CookingSessionResponse],
    summary="Get Active Cooking Session",
)
def get_active_cooking_session(
    recipe_id: Optional[str] = Query(None, description="Optional recipe ID to check for an active session"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Retrieve the user's active (or paused) cooking session, optionally filtered by recipe ID.
    """
    service = CookingSessionService(db)
    return service.get_active_session(user_id=user.id, recipe_id=recipe_id)


@router.get(
    "/sessions/{session_id}",
    response_model=CookingSessionResponse,
    summary="Get Cooking Session Details",
)
def get_cooking_session(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Retrieve details of an existing cooking session by ID."""
    service = CookingSessionService(db)
    return service.get_session(session_id=session_id, user_id=user.id)


@router.put(
    "/sessions/{session_id}",
    response_model=CookingSessionResponse,
    summary="Update Cooking Session",
)
@router.patch(
    "/sessions/{session_id}",
    response_model=CookingSessionResponse,
    summary="Patch Cooking Session",
)
def update_cooking_session(
    session_id: str,
    body: CookingSessionUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update current step, status, notes, servings, or prepared ingredients."""
    service = CookingSessionService(db)
    return service.update_session(session_id=session_id, payload=body, user_id=user.id)


@router.post(
    "/sessions/{session_id}/next",
    response_model=CookingSessionResponse,
    summary="Move to Next Step",
)
def next_cooking_step(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Move to the next step of the recipe in the cooking session."""
    service = CookingSessionService(db)
    return service.next_step(session_id=session_id, user_id=user.id)


@router.post(
    "/sessions/{session_id}/previous",
    response_model=CookingSessionResponse,
    summary="Move to Previous Step",
)
def previous_cooking_step(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Move to the previous step of the recipe in the cooking session."""
    service = CookingSessionService(db)
    return service.previous_step(session_id=session_id, user_id=user.id)


@router.post(
    "/sessions/{session_id}/pause",
    response_model=CookingSessionResponse,
    summary="Pause Cooking Session",
)
def pause_cooking_session(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Pause an active cooking session without losing step progress."""
    service = CookingSessionService(db)
    return service.pause_session(session_id=session_id, user_id=user.id)


@router.post(
    "/sessions/{session_id}/resume",
    response_model=CookingSessionResponse,
    summary="Resume Cooking Session",
)
def resume_cooking_session(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Resume a paused cooking session."""
    service = CookingSessionService(db)
    return service.resume_session(session_id=session_id, user_id=user.id)


@router.post(
    "/sessions/{session_id}/complete",
    response_model=CookingSessionResponse,
    summary="Complete Cooking Session",
)
def complete_cooking_session(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Mark the cooking session as completed and set completion timestamp."""
    service = CookingSessionService(db)
    return service.complete_session(session_id=session_id, user_id=user.id)


@router.get(
    "/sessions/{session_id}/preparation-checklist",
    response_model=PreparationChecklistResponse,
    summary="Get Ingredient Preparation Checklist",
)
def get_preparation_checklist(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Get the recipe's ingredients scaled to the session's serving count,
    including preparation notes and current prepared state.
    """
    service = CookingSessionService(db)
    return service.get_preparation_checklist(session_id=session_id, user_id=user.id)


@router.put(
    "/sessions/{session_id}/prepared-ingredients",
    response_model=CookingSessionResponse,
    summary="Update Prepared Ingredients",
)
def update_prepared_ingredients(
    session_id: str,
    body: PreparedIngredientsUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Persist the list of prepared ingredient IDs/names for the cooking session.
    """
    service = CookingSessionService(db)
    return service.update_prepared_ingredients(
        session_id=session_id,
        prepared_ingredients=body.prepared_ingredients,
        user_id=user.id,
    )


class CookingContextResponse(BaseModel):
    session_id: str
    recipe_id: str
    recipe_name: str
    status: str
    current_step: int
    total_steps: int
    servings: int
    scale_factor: float
    current_instruction: Optional[str]
    next_instruction: Optional[str]
    previous_instruction: Optional[str]
    ingredients: list
    prepared_ingredients: List[str]
    progress_pct: float


@router.get(
    "/context/{session_id}",
    response_model=CookingContextResponse,
    summary="Get Structured Cooking Context",
    description=(
        "Returns structured cooking context for the AI cooking assistant: "
        "current step instruction, next step, previous step, ingredients, and progress."
    ),
)
def get_cooking_context(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Returns rich structured context about the current cooking session.
    """
    from app.models.cooking_session import CookingSession
    from app.models.recipe import Recipe

    session = db.query(CookingSession).filter(CookingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Cooking session '{session_id}' not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this cooking session")

    recipe = db.query(Recipe).filter(Recipe.id == session.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe not found for session '{session_id}'")

    steps = recipe.legacy_instructions
    total_steps = len(steps)
    current_step = session.current_step or 0

    def get_step(idx: int) -> Optional[str]:
        if 0 <= idx < total_steps:
            return steps[idx]
        return None

    current_instruction = get_step(current_step)
    next_instruction = get_step(current_step + 1)
    previous_instruction = get_step(current_step - 1) if current_step > 0 else None

    base_servings = recipe.servings if recipe.servings and recipe.servings > 0 else 4
    session_servings = session.servings if session.servings and session.servings > 0 else base_servings
    scale_factor = round(session_servings / base_servings, 3)

    ingredients = [
        {
            "id": ri.id,
            "name": ri.ingredient.canonical_name if ri.ingredient else ri.raw_text,
            "quantity": ri.quantity,
            "scaled_quantity": round(ri.quantity * scale_factor, 2) if ri.quantity is not None else None,
            "unit": ri.unit,
            "preparation_note": ri.preparation_note,
            "raw_text": ri.raw_text,
        }
        for ri in (recipe.ingredients or [])
    ]

    progress_pct = round((current_step / total_steps) * 100, 1) if total_steps > 0 else 0.0

    return CookingContextResponse(
        session_id=session_id,
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        status=session.status or "active",
        current_step=current_step,
        total_steps=total_steps,
        servings=session_servings,
        scale_factor=scale_factor,
        current_instruction=current_instruction,
        next_instruction=next_instruction,
        previous_instruction=previous_instruction,
        ingredients=ingredients,
        prepared_ingredients=session.prepared_ingredients or [],
        progress_pct=progress_pct,
    )


# ---------------------------------------------------------------------------
# Phase 11 — Cooking Timers Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/timers",
    response_model=CookingTimerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Cooking Timer",
)
def create_cooking_timer(
    body: CookingTimerCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Create a new cooking timer associated with a recipe, session, or specific step.
    Optionally starts the timer immediately.
    """
    service = CookingTimerService(db)
    return service.create_timer(user_id=user.id, payload=body)


@router.get(
    "/timers",
    response_model=List[CookingTimerResponse],
    summary="List Cooking Timers",
)
def list_cooking_timers(
    cooking_session_id: Optional[str] = Query(None, description="Filter by cooking session ID"),
    recipe_id: Optional[str] = Query(None, description="Filter by recipe ID"),
    status: Optional[str] = Query(None, description="Filter by timer status (idle, running, paused, completed, cancelled)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Retrieve all timers for the current user, synchronized drift-free to real-time.
    """
    service = CookingTimerService(db)
    return service.list_timers(
        user_id=user.id,
        cooking_session_id=cooking_session_id,
        recipe_id=recipe_id,
        status_filter=status,
    )


@router.get(
    "/timers/{timer_id}",
    response_model=CookingTimerResponse,
    summary="Get Cooking Timer",
)
def get_cooking_timer(
    timer_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Get current status and remaining time for a specific timer.
    """
    service = CookingTimerService(db)
    return service.get_timer(timer_id=timer_id, user_id=user.id)


@router.post(
    "/timers/{timer_id}/start",
    response_model=CookingTimerResponse,
    summary="Start Cooking Timer",
)
def start_cooking_timer(
    timer_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Start or restart a timer.
    """
    service = CookingTimerService(db)
    return service.start_timer(timer_id=timer_id, user_id=user.id)


@router.post(
    "/timers/{timer_id}/pause",
    response_model=CookingTimerResponse,
    summary="Pause Cooking Timer",
)
def pause_cooking_timer(
    timer_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Pause a running timer, preserving the remaining duration.
    """
    service = CookingTimerService(db)
    return service.pause_timer(timer_id=timer_id, user_id=user.id)


@router.post(
    "/timers/{timer_id}/resume",
    response_model=CookingTimerResponse,
    summary="Resume Cooking Timer",
)
def resume_cooking_timer(
    timer_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Resume a paused timer.
    """
    service = CookingTimerService(db)
    return service.resume_timer(timer_id=timer_id, user_id=user.id)


@router.post(
    "/timers/{timer_id}/cancel",
    response_model=CookingTimerResponse,
    summary="Cancel Cooking Timer",
)
def cancel_cooking_timer(
    timer_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Cancel an active or paused timer.
    """
    service = CookingTimerService(db)
    return service.cancel_timer(timer_id=timer_id, user_id=user.id)


@router.post(
    "/timers/{timer_id}/reset",
    response_model=CookingTimerResponse,
    summary="Reset Cooking Timer",
)
def reset_cooking_timer(
    timer_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Reset a timer back to its configured duration and idle state.
    """
    service = CookingTimerService(db)
    return service.reset_timer(timer_id=timer_id, user_id=user.id)


@router.delete(
    "/timers/{timer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Cooking Timer",
)
def delete_cooking_timer(
    timer_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Delete / dismiss a timer.
    """
    service = CookingTimerService(db)
    service.delete_timer(timer_id=timer_id, user_id=user.id)
    return None


# ---------------------------------------------------------------------------
# Phase 12 — Contextual AI Cooking Companion
# ---------------------------------------------------------------------------

@router.post(
    "/companion/chat",
    response_model=CompanionChatResponse,
    summary="Cooking Companion Chat",
    description="Context-aware cooking guidance for active sessions, with deterministic fallback.",
)
async def cooking_companion_chat(
    body: CompanionChatRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Ask a question while cooking. Responds using recipe, step, timers, and pantry context.
    Falls back gracefully to deterministic rule-based advice if no external provider is configured.
    """
    clean_msg = body.message.strip() if body.message else ""
    if not clean_msg:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty or whitespace only",
        )
    if len(clean_msg) > 1000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message exceeds maximum allowed length of 1000 characters",
        )

    service = CookingCompanionService(db)
    return await service.chat(user_id=user.id, payload=body)

