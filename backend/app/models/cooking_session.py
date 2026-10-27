import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, CheckConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CookingSession(Base):
    __tablename__ = "cooking_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    recipe_id: Mapped[str] = mapped_column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), index=True, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    servings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    prepared_ingredients: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="cooking_sessions")
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="cooking_sessions")
    timers: Mapped[List["CookingTimer"]] = relationship("CookingTimer", back_populates="cooking_session", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("current_step >= 0", name="chk_cooking_session_current_step_non_negative"),
        CheckConstraint("status IN ('active', 'paused', 'completed')", name="chk_cooking_session_status_valid"),
        CheckConstraint("servings IS NULL OR servings > 0", name="chk_cooking_session_servings_positive"),
    )


class CookingTimer(Base):
    __tablename__ = "cooking_timers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    cooking_session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("cooking_sessions.id", ondelete="SET NULL"), index=True, nullable=True)
    recipe_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("recipes.id", ondelete="SET NULL"), index=True, nullable=True)
    step_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="idle", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="cooking_timers")
    cooking_session: Mapped[Optional["CookingSession"]] = relationship("CookingSession", back_populates="timers")
    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")

    __table_args__ = (
        CheckConstraint("duration_seconds > 0 AND duration_seconds <= 86400", name="chk_cooking_timer_duration_valid"),
        CheckConstraint("remaining_seconds >= 0", name="chk_cooking_timer_remaining_non_negative"),
        CheckConstraint("status IN ('idle', 'running', 'paused', 'completed', 'cancelled')", name="chk_cooking_timer_status_valid"),
    )
