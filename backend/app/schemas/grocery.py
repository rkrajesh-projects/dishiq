from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProductPriceRead(BaseModel):
    id: str
    price: float
    currency: str = Field(default="INR", description="Currency code for the price (ISO 4217)")
    delivery_fee: float
    observed_at: datetime
    data_source_type: str = Field(..., description="Source type, explicitly identified as 'demo'")

    model_config = ConfigDict(from_attributes=True)


class GroceryProductRead(BaseModel):
    id: str
    store_id: str
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
