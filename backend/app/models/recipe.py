import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cuisine: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    dietary_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    preparation_minutes: Mapped[int] = mapped_column(Integer, default=0)
    cooking_minutes: Mapped[int] = mapped_column(Integer, default=0)
    servings: Mapped[int] = mapped_column(Integer, default=4)
    instructions: Mapped[list] = mapped_column(JSON, default=list)  # List of step strings
    source_name: Mapped[str] = mapped_column(String(255), default="DishIQ Kitchen")
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    average_rating: Mapped[float] = mapped_column(Float, default=4.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan", lazy="joined"
    )
    feedbacks: Mapped[List["RecipeFeedback"]] = relationship(
        "RecipeFeedback", back_populates="recipe", cascade="all, delete-orphan"
    )
    cooking_sessions: Mapped[List["CookingSession"]] = relationship(
        "CookingSession", back_populates="recipe", cascade="all, delete-orphan"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    default_unit: Mapped[str] = mapped_column(String(50), default="grams")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    recipe_ingredients: Mapped[List["RecipeIngredient"]] = relationship("RecipeIngredient", back_populates="ingredient")
    pantry_items: Mapped[List["PantryItem"]] = relationship("PantryItem", back_populates="ingredient")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    recipe_id: Mapped[str] = mapped_column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False)
    raw_text: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    preparation_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="recipe_ingredients", lazy="joined")
