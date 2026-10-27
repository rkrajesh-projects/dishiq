import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, JSON, CheckConstraint
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
    source_recipe_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    source_license: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="UNVERIFIED")
    verification_level: Mapped[str] = mapped_column(String(50), default="NONE")
    dataset_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    original_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    original_language: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_indian_recipe: Mapped[bool] = mapped_column(Integer, default=0) # using Integer as boolean in SQLite
    collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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

    __table_args__ = (
        CheckConstraint("preparation_minutes >= 0", name="chk_recipe_prep_time_non_negative"),
        CheckConstraint("cooking_minutes >= 0", name="chk_recipe_cook_time_non_negative"),
        CheckConstraint("servings > 0", name="chk_recipe_servings_positive"),
    )

    @property
    def legacy_instructions(self) -> list:
        if not self.instructions:
            return []
        if isinstance(self.instructions[0], dict):
            return [step.get("text", "") for step in self.instructions]
        return self.instructions

    @property
    def structured_instructions_data(self) -> Optional[list]:
        if not self.instructions:
            return None
        if isinstance(self.instructions[0], dict):
            return self.instructions
        return None


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
    recipe_id: Mapped[str] = mapped_column(String(36), ForeignKey("recipes.id", ondelete="CASCADE"), index=True, nullable=False)
    ingredient_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingredients.id", ondelete="CASCADE"), index=True, nullable=False)
    raw_text: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    preparation_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="recipe_ingredients", lazy="joined")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_recipe_ingredient_quantity_positive"),
    )
