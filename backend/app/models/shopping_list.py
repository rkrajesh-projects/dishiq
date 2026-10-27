import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Float, Integer, Text, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    meal_plan_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("meal_plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, completed, archived
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="shopping_lists")
    meal_plan: Mapped[Optional["MealPlan"]] = relationship("MealPlan", back_populates="shopping_lists")
    items: Mapped[List["ShoppingListItem"]] = relationship(
        "ShoppingListItem",
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        order_by="ShoppingListItem.created_at.asc()",
    )


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    shopping_list_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ingredient_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ingredient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    required_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(50), default="piece")
    pantry_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    quantity_to_buy: Mapped[float] = mapped_column(Float, default=0.0)
    user_quantity_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_obtained: Mapped[bool] = mapped_column(Integer, default=0)
    is_manual: Mapped[bool] = mapped_column(Integer, default=0)
    source_recipes: Mapped[list] = mapped_column(JSON, default=list)
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
    shopping_list: Mapped["ShoppingList"] = relationship("ShoppingList", back_populates="items")
    ingredient: Mapped[Optional["Ingredient"]] = relationship("Ingredient", lazy="joined")

    __table_args__ = (
        CheckConstraint("required_quantity >= 0", name="chk_sli_required_quantity_non_negative"),
        CheckConstraint("quantity_to_buy >= 0", name="chk_sli_quantity_to_buy_non_negative"),
    )
