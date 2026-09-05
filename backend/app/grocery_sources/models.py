from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator

class NormalizedGroceryProduct(BaseModel):
    """
    Pydantic model representing a unified internal representation of a grocery product
    fetched from any real-time external source or demo repository.
    """
    source_platform: str = Field(..., description="Unique code identifier of the external provider (e.g. 'quickmart')")
    source_product_id: str = Field(..., description="Platform-specific unique ID of the product")
    store_name: str = Field(..., description="Store display name")
    product_name: str = Field(..., description="Display name of the product")
    brand: Optional[str] = Field("Generic", description="Product brand name")
    category: Optional[str] = Field("Uncategorized", description="Product category")
    package_quantity: Optional[float] = Field(1.0, description="Package size amount (e.g. 200.0)")
    package_unit: Optional[str] = Field("pack", description="Package size unit (e.g. grams, kg, ml)")
    price: Optional[float] = Field(None, description="Current price in INR (₹)")
    currency: str = Field(default="INR", description="Currency code (always INR)")
    availability: bool = Field(default=True, description="Whether the product is currently in stock")
    product_url: Optional[str] = Field(None, description="Optional direct URL link to product page")
    retrieved_at: datetime = Field(..., description="Timestamp of when the product details were retrieved")
    price_freshness: Literal["LIVE", "CACHED", "UNKNOWN"] = Field(
        default="LIVE", description="Freshness status indicator for the retrieved price"
    )

    @model_validator(mode="before")
    @classmethod
    def apply_defaults(cls, data):
        if isinstance(data, dict):
            if data.get("brand") is None:
                data["brand"] = "Generic"
            if data.get("category") is None:
                data["category"] = "Uncategorized"
        return data
