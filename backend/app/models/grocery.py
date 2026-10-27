import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, Float, DateTime, ForeignKey, CheckConstraint, Index
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
    source_product_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
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
    prices: Mapped[List["ProductPrice"]] = relationship(
        "ProductPrice",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="joined",
        order_by="ProductPrice.observed_at.asc()"
    )

    @property
    def latest_price(self) -> Optional[float]:
        if not self.prices:
            return None
        return self.prices[-1].price

    __table_args__ = (
        Index("ix_grocery_products_store_source_id", "store_id", "source_product_id"),
        Index("ix_grocery_products_store_name_pkg", "store_id", "name", "package_quantity", "package_unit"),
    )


class ProductPrice(Base):
    __tablename__ = "product_prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("grocery_products.id", ondelete="CASCADE"), index=True, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    price_freshness: Mapped[str] = mapped_column(String(50), default="CACHED", nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    data_source_type: Mapped[str] = mapped_column(String(50), default="demo", nullable=False)

    product: Mapped["GroceryProduct"] = relationship("GroceryProduct", back_populates="prices")

    __table_args__ = (
        CheckConstraint("price >= 0", name="chk_product_price_non_negative"),
        CheckConstraint("delivery_fee >= 0", name="chk_product_delivery_fee_non_negative"),
        Index("ix_product_prices_product_observed", "product_id", "observed_at"),
    )
