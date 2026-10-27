import uuid
from datetime import datetime, timezone, date
from typing import List, Optional
from sqlalchemy import String, Integer, Text, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="meal_plans")
    meals: Mapped[List["MealPlanItem"]] = relationship(
        "MealPlanItem",
        back_populates="meal_plan",
        cascade="all, delete-orphan",
        order_by="MealPlanItem.meal_date.asc()",
    )
    shopping_lists: Mapped[List["ShoppingList"]] = relationship(
        "ShoppingList", back_populates="meal_plan", cascade="all, delete-orphan"
    )


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    meal_plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    meal_type: Mapped[str] = mapped_column(String(50), default="dinner")  # breakfast, lunch, dinner, snack
    servings: Mapped[int] = mapped_column(Integer, default=2)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    meal_plan: Mapped["MealPlan"] = relationship("MealPlan", back_populates="meals")
    recipe: Mapped["Recipe"] = relationship("Recipe", lazy="joined")

    __table_args__ = (
        CheckConstraint("servings > 0", name="chk_meal_plan_item_servings_positive"),
    )
