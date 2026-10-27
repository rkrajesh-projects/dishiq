import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    preference: Mapped["UserPreference"] = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    pantry_items: Mapped[list["PantryItem"]] = relationship("PantryItem", back_populates="user", cascade="all, delete-orphan")
    feedbacks: Mapped[list["RecipeFeedback"]] = relationship("RecipeFeedback", back_populates="user", cascade="all, delete-orphan")
    cooking_sessions: Mapped[list["CookingSession"]] = relationship("CookingSession", back_populates="user", cascade="all, delete-orphan")
    cooking_timers: Mapped[list["CookingTimer"]] = relationship("CookingTimer", back_populates="user", cascade="all, delete-orphan")
    meal_plans: Mapped[list["MealPlan"]] = relationship("MealPlan", back_populates="user", cascade="all, delete-orphan")
    shopping_lists: Mapped[list["ShoppingList"]] = relationship("ShoppingList", back_populates="user", cascade="all, delete-orphan")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    dietary_type: Mapped[str] = mapped_column(String(100), default="None")
    weekly_budget: Mapped[float] = mapped_column(Float, default=150.0)
    household_size: Mapped[int] = mapped_column(Integer, default=1)
    disliked_ingredients: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", back_populates="preference")
