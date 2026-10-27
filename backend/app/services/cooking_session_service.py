from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import DishIQException
from app.models.cooking_session import CookingSession
from app.models.recipe import Recipe
from app.models.user import User
from app.repositories.cooking_session_repository import CookingSessionRepository
from app.schemas.cooking_session import (
    CookingSessionCreate,
    CookingSessionUpdate,
    CookingSessionResponse,
    PreparationItem,
    PreparationChecklistResponse,
)


class CookingSessionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CookingSessionRepository(db)

    def _verify_recipe_exists(self, recipe_id: str) -> Recipe:
        recipe = self.db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise DishIQException(
                message=f"Recipe with ID '{recipe_id}' not found.",
                code="RECIPE_NOT_FOUND",
                status_code=404
            )
        return recipe

    def _verify_user_exists(self, user_id: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise DishIQException(
                message=f"User with ID '{user_id}' not found.",
                code="USER_NOT_FOUND",
                status_code=404
            )
        return user

    def _verify_ownership(self, session: CookingSession, user_id: Optional[str]) -> None:
        if user_id is not None and session.user_id != user_id:
            raise DishIQException(
                message="You do not have permission to access or modify this cooking session.",
                code="FORBIDDEN",
                status_code=403
            )

    def create_session(self, user_id: str, payload: CookingSessionCreate) -> CookingSessionResponse:
        self._verify_user_exists(user_id)
        recipe = self._verify_recipe_exists(payload.recipe_id)

        # Determine session servings (defaulting to recipe baseline servings if omitted)
        servings = payload.servings if payload.servings and payload.servings > 0 else (recipe.servings or 4)

        session = self.repo.create(
            user_id=user_id,
            recipe_id=payload.recipe_id,
            notes=payload.notes,
            servings=servings,
            prepared_ingredients=[],
        )
        return CookingSessionResponse.model_validate(session)

    def get_session(self, session_id: str, user_id: Optional[str] = None) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        self._verify_ownership(session, user_id)
        return CookingSessionResponse.model_validate(session)

    def list_sessions_for_user(self, user_id: str) -> List[CookingSessionResponse]:
        self._verify_user_exists(user_id)
        sessions = self.repo.list_for_user(user_id)
        return [CookingSessionResponse.model_validate(s) for s in sessions]

    def get_active_session(self, user_id: str, recipe_id: Optional[str] = None) -> Optional[CookingSessionResponse]:
        self._verify_user_exists(user_id)
        if recipe_id:
            session = self.repo.get_active_for_user_and_recipe(user_id, recipe_id)
        else:
            session = self.repo.get_active_for_user(user_id)
        if not session:
            return None
        return CookingSessionResponse.model_validate(session)

    def update_session(self, session_id: str, payload: CookingSessionUpdate, user_id: Optional[str] = None) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        self._verify_ownership(session, user_id)

        # Prevent stale step modifications on completed sessions
        if session.status == "completed" and payload.current_step is not None and payload.current_step != session.current_step:
            raise DishIQException(
                message="Cannot navigate or update steps on a completed session.",
                code="SESSION_COMPLETED",
                status_code=400
            )

        if payload.current_step is not None:
            if payload.current_step < 0:
                raise DishIQException(
                    message="current_step cannot be negative.",
                    code="INVALID_STEP",
                    status_code=400
                )
            recipe = session.recipe
            instructions = recipe.instructions if recipe and recipe.instructions else []
            if instructions and payload.current_step >= len(instructions):
                session.current_step = len(instructions) - 1
            else:
                session.current_step = payload.current_step

        if payload.status is not None:
            status_val = payload.status.strip().lower()
            if status_val not in ("active", "paused", "completed"):
                raise DishIQException(
                    message="status must be 'active', 'paused', or 'completed'.",
                    code="INVALID_STATUS",
                    status_code=400
                )
            
            # Handle transition to completed
            if status_val == "completed" and session.status != "completed":
                session.completed_at = datetime.now(timezone.utc)
            elif status_val != "completed":
                # Avoid setting completed_at for active/paused sessions
                session.completed_at = None
                
            session.status = status_val

        if payload.servings is not None:
            if payload.servings <= 0:
                raise DishIQException(
                    message="Servings must be a positive integer.",
                    code="INVALID_SERVINGS",
                    status_code=400
                )
            session.servings = payload.servings

        if payload.prepared_ingredients is not None:
            session.prepared_ingredients = payload.prepared_ingredients

        if payload.notes is not None:
            session.notes = payload.notes

        if payload.completed_at is not None:
            if session.status == "completed":
                session.completed_at = payload.completed_at

        session.updated_at = datetime.now(timezone.utc)
        updated_session = self.repo.save(session)
        return CookingSessionResponse.model_validate(updated_session)

    def next_step(self, session_id: str, user_id: Optional[str] = None) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        self._verify_ownership(session, user_id)
        
        if session.status == "completed":
            raise DishIQException(
                message="Cannot navigate steps on a completed session.",
                code="SESSION_COMPLETED",
                status_code=400
            )

        recipe = session.recipe
        instructions = recipe.instructions if recipe and recipe.instructions else []
        total_steps = len(instructions)

        if total_steps == 0:
            raise DishIQException(
                message="This recipe has no instructions to navigate.",
                code="NO_INSTRUCTIONS",
                status_code=400
            )

        max_step = total_steps - 1
        if session.current_step < max_step:
            session.current_step += 1
            session.updated_at = datetime.now(timezone.utc)
            self.repo.save(session)

        return CookingSessionResponse.model_validate(session)

    def previous_step(self, session_id: str, user_id: Optional[str] = None) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        self._verify_ownership(session, user_id)

        if session.status == "completed":
            raise DishIQException(
                message="Cannot navigate steps on a completed session.",
                code="SESSION_COMPLETED",
                status_code=400
            )

        if session.current_step > 0:
            session.current_step -= 1
            session.updated_at = datetime.now(timezone.utc)
            self.repo.save(session)

        return CookingSessionResponse.model_validate(session)

    def pause_session(self, session_id: str, user_id: Optional[str] = None) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        self._verify_ownership(session, user_id)

        if session.status == "completed":
            raise DishIQException(
                message="Cannot pause a completed cooking session.",
                code="SESSION_COMPLETED",
                status_code=400
            )

        session.status = "paused"
        session.updated_at = datetime.now(timezone.utc)
        self.repo.save(session)
        return CookingSessionResponse.model_validate(session)

    def resume_session(self, session_id: str, user_id: Optional[str] = None) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        self._verify_ownership(session, user_id)

        if session.status == "completed":
            raise DishIQException(
                message="Cannot resume a completed cooking session.",
                code="SESSION_COMPLETED",
                status_code=400
            )

        session.status = "active"
        session.updated_at = datetime.now(timezone.utc)
        self.repo.save(session)
        return CookingSessionResponse.model_validate(session)

    def complete_session(self, session_id: str, user_id: Optional[str] = None) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        self._verify_ownership(session, user_id)

        if session.status != "completed":
            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)
            session.updated_at = datetime.now(timezone.utc)
            self.repo.save(session)

        return CookingSessionResponse.model_validate(session)

    def update_prepared_ingredients(
        self, session_id: str, prepared_ingredients: List[str], user_id: Optional[str] = None
    ) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        self._verify_ownership(session, user_id)

        session.prepared_ingredients = prepared_ingredients
        session.updated_at = datetime.now(timezone.utc)
        self.repo.save(session)
        return CookingSessionResponse.model_validate(session)

    def get_preparation_checklist(
        self, session_id: str, user_id: Optional[str] = None
    ) -> PreparationChecklistResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        self._verify_ownership(session, user_id)

        recipe = session.recipe
        base_servings = recipe.servings if recipe.servings and recipe.servings > 0 else 4
        session_servings = session.servings if session.servings and session.servings > 0 else base_servings
        scale_factor = session_servings / base_servings

        prepared_set = set(session.prepared_ingredients or [])
        items: List[PreparationItem] = []

        for ri in (recipe.ingredients or []):
            raw_lower = (ri.raw_text or "").lower()
            is_to_taste = any(phrase in raw_lower for phrase in ("to taste", "as needed", "a pinch", "optional"))

            scaled_qty: Optional[float] = None
            if ri.quantity is not None and not is_to_taste:
                scaled_qty = round(ri.quantity * scale_factor, 2)
                if scaled_qty.is_integer():
                    scaled_qty = float(int(scaled_qty))
            elif ri.quantity is not None:
                scaled_qty = float(ri.quantity)

            canonical = ri.ingredient.canonical_name if ri.ingredient else ri.raw_text
            is_prep = (ri.id in prepared_set) or (canonical in prepared_set)

            items.append(
                PreparationItem(
                    id=ri.id,
                    ingredient_id=ri.ingredient_id,
                    name=canonical,
                    raw_text=ri.raw_text,
                    quantity=ri.quantity,
                    scaled_quantity=scaled_qty,
                    unit=ri.unit,
                    preparation_note=ri.preparation_note,
                    category=ri.ingredient.category if ri.ingredient else None,
                    is_prepared=is_prep,
                    to_taste=is_to_taste,
                )
            )

        total_ingredients = len(items)
        prepared_count = sum(1 for it in items if it.is_prepared)
        all_prepared = (prepared_count == total_ingredients) if total_ingredients > 0 else False

        return PreparationChecklistResponse(
            session_id=session.id,
            recipe_id=recipe.id,
            recipe_name=recipe.name,
            servings=session_servings,
            base_servings=base_servings,
            scale_factor=round(scale_factor, 3),
            total_ingredients=total_ingredients,
            prepared_count=prepared_count,
            all_prepared=all_prepared,
            items=items,
        )
