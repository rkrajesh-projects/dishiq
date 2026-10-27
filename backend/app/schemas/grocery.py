from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProductPriceRead(BaseModel):
    id: str
    price: float
    currency: str = Field(default="INR", description="Currency code for the price (ISO 4217)")
    price_freshness: str = Field(default="CACHED", description="Freshness status indicator for the price")
    delivery_fee: float
    observed_at: datetime
    data_source_type: str = Field(..., description="Source type, e.g. 'demo' or 'live'")

    model_config = ConfigDict(from_attributes=True)


class GroceryProductRead(BaseModel):
    id: str
    store_id: str
    source_product_id: Optional[str] = None
    name: str
    normalized_name: str
    brand: str
    package_quantity: float
    package_unit: str
    category: str
    in_stock: bool
    prices: List[ProductPriceRead]

    model_config = ConfigDict(from_attributes=True)


class GroceryStoreRead(BaseModel):
    id: str
    name: str
    store_type: str
    city: str
    is_demo_store: bool = Field(..., description="Identifies store as demonstration data")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductPriceHistoryItem(BaseModel):
    id: str
    price: float
    delivery_fee: float = 0.0
    currency: str = "INR"
    price_freshness: str = "CACHED"
    data_source_type: str = "demo"
    observed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductPriceHistoryResponse(BaseModel):
    product_id: str
    product_name: str
    store_name: str
    brand: Optional[str] = None
    package_quantity: Optional[float] = None
    package_unit: Optional[str] = None
    current_price: Optional[float] = None
    history_count: int
    prices: List[ProductPriceHistoryItem]

    model_config = ConfigDict(from_attributes=True)
