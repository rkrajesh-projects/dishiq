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
            CookingSession.status == "active"
        ).order_by(CookingSession.started_at.desc()).first()

    def create(self, user_id: str, recipe_id: str, notes: Optional[str] = None) -> CookingSession:
        session = CookingSession(
            user_id=user_id,
            recipe_id=recipe_id,
            notes=notes,
            status="active",
            current_step=0
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def save(self, session: CookingSession) -> CookingSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
