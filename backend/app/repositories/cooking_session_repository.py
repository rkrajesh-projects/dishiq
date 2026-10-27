from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.cooking_session import CookingSession


class CookingSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, session_id: str) -> Optional[CookingSession]:
        return self.db.query(CookingSession).filter(CookingSession.id == session_id).first()

    def list_for_user(self, user_id: str) -> List[CookingSession]:
        return self.db.query(CookingSession).filter(CookingSession.user_id == user_id).order_by(CookingSession.started_at.desc()).all()

    def get_active_for_user(self, user_id: str) -> Optional[CookingSession]:
        return self.db.query(CookingSession).filter(
            CookingSession.user_id == user_id,
            CookingSession.status.in_(["active", "paused"])
        ).order_by(CookingSession.started_at.desc()).first()

    def get_active_for_user_and_recipe(self, user_id: str, recipe_id: str) -> Optional[CookingSession]:
        return self.db.query(CookingSession).filter(
            CookingSession.user_id == user_id,
            CookingSession.recipe_id == recipe_id,
            CookingSession.status.in_(["active", "paused"])
        ).order_by(CookingSession.started_at.desc()).first()

    def create(
        self,
        user_id: str,
        recipe_id: str,
        notes: Optional[str] = None,
        servings: Optional[int] = None,
        prepared_ingredients: Optional[List[str]] = None,
    ) -> CookingSession:
        session = CookingSession(
            user_id=user_id,
            recipe_id=recipe_id,
            notes=notes,
            servings=servings,
            prepared_ingredients=prepared_ingredients or [],
            status="active",
            current_step=0
        )
        try:
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return session
        except Exception:
            self.db.rollback()
            raise

    def save(self, session: CookingSession) -> CookingSession:
        try:
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return session
        except Exception:
            self.db.rollback()
            raise
