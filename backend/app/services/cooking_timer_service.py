from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.cooking_session import CookingTimer, CookingSession
from app.schemas.cooking_timer import CookingTimerCreate, CookingTimerUpdate


class CookingTimerService:
    def __init__(self, db: Session):
        self.db = db

    def _verify_ownership(self, timer: CookingTimer, user_id: str) -> None:
        if timer.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access or modify this timer."
            )

    def _sync_timer_drift(self, timer: CookingTimer) -> CookingTimer:
        """
        Derives real-time remaining seconds and completes expired timers drift-free.
        Formula: remaining = max(0, ends_at - now)
        """
        if timer.status == "running" and timer.ends_at:
            now = datetime.now(timezone.utc)
            # Ensure timezone awareness
            ends_at = timer.ends_at if timer.ends_at.tzinfo else timer.ends_at.replace(tzinfo=timezone.utc)
            diff = (ends_at - now).total_seconds()
            if diff <= 0:
                timer.remaining_seconds = 0.0
                timer.status = "completed"
                timer.completed_at = now
                timer.ends_at = None
                self.db.add(timer)
                self.db.commit()
                self.db.refresh(timer)
            else:
                timer.remaining_seconds = round(diff, 2)
        return timer

    def create_timer(self, user_id: str, payload: CookingTimerCreate) -> CookingTimer:
        if payload.duration_seconds <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duration must be a positive integer in seconds."
            )
        if payload.duration_seconds > 86400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duration cannot exceed 24 hours (86400 seconds)."
            )

        if payload.cooking_session_id:
            session = self.db.query(CookingSession).filter(CookingSession.id == payload.cooking_session_id).first()
            if not session or session.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Cooking session '{payload.cooking_session_id}' not found for user."
                )

        now = datetime.now(timezone.utc)
        timer = CookingTimer(
            user_id=user_id,
            cooking_session_id=payload.cooking_session_id,
            recipe_id=payload.recipe_id,
            step_index=payload.step_index,
            label=payload.label.strip(),
            duration_seconds=payload.duration_seconds,
            remaining_seconds=float(payload.duration_seconds),
            status="idle",
            created_at=now,
            updated_at=now,
        )

        if payload.auto_start:
            timer.status = "running"
            timer.started_at = now
            timer.ends_at = now + timedelta(seconds=payload.duration_seconds)

        self.db.add(timer)
        self.db.commit()
        self.db.refresh(timer)
        return timer

    def list_timers(
        self,
        user_id: str,
        cooking_session_id: Optional[str] = None,
        recipe_id: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[CookingTimer]:
        query = self.db.query(CookingTimer).filter(CookingTimer.user_id == user_id)
        if cooking_session_id:
            query = query.filter(CookingTimer.cooking_session_id == cooking_session_id)
        if recipe_id:
            query = query.filter(CookingTimer.recipe_id == recipe_id)
        if status_filter:
            query = query.filter(CookingTimer.status == status_filter)

        timers = query.order_by(CookingTimer.created_at.desc()).all()
        return [self._sync_timer_drift(t) for t in timers]

    def get_timer(self, timer_id: str, user_id: str) -> CookingTimer:
        timer = self.db.query(CookingTimer).filter(CookingTimer.id == timer_id).first()
        if not timer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timer '{timer_id}' not found."
            )
        self._verify_ownership(timer, user_id)
        return self._sync_timer_drift(timer)

    def start_timer(self, timer_id: str, user_id: str) -> CookingTimer:
        timer = self.get_timer(timer_id, user_id)
        if timer.status == "running":
            return timer

        now = datetime.now(timezone.utc)
        target_remaining = timer.remaining_seconds if timer.remaining_seconds > 0 else float(timer.duration_seconds)
        timer.status = "running"
        timer.started_at = timer.started_at or now
        timer.ends_at = now + timedelta(seconds=target_remaining)
        timer.paused_at = None
        timer.updated_at = now
        self.db.commit()
        self.db.refresh(timer)
        return self._sync_timer_drift(timer)

    def pause_timer(self, timer_id: str, user_id: str) -> CookingTimer:
        timer = self.get_timer(timer_id, user_id)
        if timer.status != "running":
            return timer

        now = datetime.now(timezone.utc)
        ends_at = timer.ends_at if timer.ends_at.tzinfo else timer.ends_at.replace(tzinfo=timezone.utc)
        remaining = max(0.0, (ends_at - now).total_seconds())

        timer.status = "paused"
        timer.remaining_seconds = round(remaining, 2)
        timer.paused_at = now
        timer.ends_at = None
        timer.updated_at = now
        self.db.commit()
        self.db.refresh(timer)
        return timer

    def resume_timer(self, timer_id: str, user_id: str) -> CookingTimer:
        timer = self.get_timer(timer_id, user_id)
        if timer.status != "paused":
            return timer

        now = datetime.now(timezone.utc)
        remaining = timer.remaining_seconds if timer.remaining_seconds > 0 else float(timer.duration_seconds)
        timer.status = "running"
        timer.ends_at = now + timedelta(seconds=remaining)
        timer.paused_at = None
        timer.updated_at = now
        self.db.commit()
        self.db.refresh(timer)
        return self._sync_timer_drift(timer)

    def cancel_timer(self, timer_id: str, user_id: str) -> CookingTimer:
        timer = self.get_timer(timer_id, user_id)
        timer.status = "cancelled"
        timer.ends_at = None
        timer.paused_at = None
        timer.remaining_seconds = 0.0
        timer.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(timer)
        return timer

    def reset_timer(self, timer_id: str, user_id: str) -> CookingTimer:
        timer = self.get_timer(timer_id, user_id)
        timer.status = "idle"
        timer.remaining_seconds = float(timer.duration_seconds)
        timer.started_at = None
        timer.ends_at = None
        timer.paused_at = None
        timer.completed_at = None
        timer.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(timer)
        return timer

    def delete_timer(self, timer_id: str, user_id: str) -> None:
        timer = self.get_timer(timer_id, user_id)
        self.db.delete(timer)
        self.db.commit()
