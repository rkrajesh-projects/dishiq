import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class GroceryStore(Base):
    __tablename__ = "grocery_stores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    store_type: Mapped[str] = mapped_column(String(100), default="Supermarket")
    city: Mapped[str] = mapped_column(String(100), default="Demo City")
    is_demo_store: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    products: Mapped[List["GroceryProduct"]] = relationship("GroceryProduct", back_populates="store", cascade="all, delete-orphan")


class GroceryProduct(Base):
    __tablename__ = "grocery_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    store_id: Mapped[str] = mapped_column(String(36), ForeignKey("grocery_stores.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(100), default="Generic")
    package_quantity: Mapped[float] = mapped_column(Float, default=1.0)
    package_unit: Mapped[str] = mapped_column(String(50), default="pack")
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    store: Mapped["GroceryStore"] = relationship("GroceryStore", back_populates="products")
    prices: Mapped[List["ProductPrice"]] = relationship("ProductPrice", back_populates="product", cascade="all, delete-orphan", lazy="joined")


class ProductPrice(Base):
    __tablename__ = "product_prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("grocery_products.id", ondelete="CASCADE"), index=True, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Float, default=0.0)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    data_source_type: Mapped[str] = mapped_column(String(50), default="demo", nullable=False)

    product: Mapped["GroceryProduct"] = relationship("GroceryProduct", back_populates="prices")
