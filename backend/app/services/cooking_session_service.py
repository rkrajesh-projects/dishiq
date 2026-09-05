from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import DishIQException
from app.models.recipe import Recipe
from app.models.user import User
from app.repositories.cooking_session_repository import CookingSessionRepository
from app.schemas.cooking_session import CookingSessionCreate, CookingSessionUpdate, CookingSessionResponse


class CookingSessionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CookingSessionRepository(db)

    def _verify_recipe_exists(self, recipe_id: str) -> None:
        recipe_exists = self.db.query(Recipe).filter(Recipe.id == recipe_id).first() is not None
        if not recipe_exists:
            raise DishIQException(
                message=f"Recipe with ID '{recipe_id}' not found.",
                code="RECIPE_NOT_FOUND",
                status_code=404
            )

    def _verify_user_exists(self, user_id: str) -> None:
        user_exists = self.db.query(User).filter(User.id == user_id).first() is not None
        if not user_exists:
            raise DishIQException(
                message=f"User with ID '{user_id}' not found.",
                code="USER_NOT_FOUND",
                status_code=404
            )

    def create_session(self, user_id: str, payload: CookingSessionCreate) -> CookingSessionResponse:
        self._verify_user_exists(user_id)
        self._verify_recipe_exists(payload.recipe_id)

        session = self.repo.create(user_id, payload.recipe_id, payload.notes)
        return CookingSessionResponse.model_validate(session)

    def get_session(self, session_id: str) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        return CookingSessionResponse.model_validate(session)

    def list_sessions_for_user(self, user_id: str) -> List[CookingSessionResponse]:
        self._verify_user_exists(user_id)
        sessions = self.repo.list_for_user(user_id)
        return [CookingSessionResponse.model_validate(s) for s in sessions]

    def get_active_session(self, user_id: str) -> Optional[CookingSessionResponse]:
        self._verify_user_exists(user_id)
        session = self.repo.get_active_for_user(user_id)
        if not session:
            return None
        return CookingSessionResponse.model_validate(session)

    def update_session(self, session_id: str, payload: CookingSessionUpdate) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )

        if payload.current_step is not None:
            if payload.current_step < 0:
                raise DishIQException(
                    message="current_step cannot be negative.",
                    code="INVALID_STEP",
                    status_code=400
                )
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

        if payload.notes is not None:
            session.notes = payload.notes

        if payload.completed_at is not None:
            if session.status == "completed":
                session.completed_at = payload.completed_at

        updated_session = self.repo.save(session)
        return CookingSessionResponse.model_validate(updated_session)

    def next_step(self, session_id: str) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )
        
        if session.status == "completed":
            raise DishIQException(
                message="Cannot navigate steps on a completed session.",
                code="SESSION_COMPLETED",
                status_code=400
            )

        recipe = session.recipe
        instructions = recipe.instructions if recipe.instructions else []
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
            self.repo.save(session)

        return CookingSessionResponse.model_validate(session)

    def previous_step(self, session_id: str) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )

        if session.status == "completed":
            raise DishIQException(
                message="Cannot navigate steps on a completed session.",
                code="SESSION_COMPLETED",
                status_code=400
            )

        if session.current_step > 0:
            session.current_step -= 1
            self.repo.save(session)

        return CookingSessionResponse.model_validate(session)

    def complete_session(self, session_id: str) -> CookingSessionResponse:
        session = self.repo.get_by_id(session_id)
        if not session:
            raise DishIQException(
                message=f"Cooking session with ID '{session_id}' not found.",
                code="SESSION_NOT_FOUND",
                status_code=404
            )

        if session.status != "completed":
            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)
            self.repo.save(session)

        return CookingSessionResponse.model_validate(session)
