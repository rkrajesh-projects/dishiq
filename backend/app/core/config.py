import os
import sys
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure repository root (parent of backend directory) is in sys.path for shared imports like `ml`
root_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class Settings(BaseSettings):
    APP_NAME: str = "DishIQ"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./dishiq.db"
    LOG_LEVEL: str = "INFO"
    FRONTEND_URL: str = "http://localhost:5173"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    PRODUCT_MATCH_THRESHOLD: float = 0.40
    PRODUCT_EMBEDDINGS_ARTIFACT_PATH: str = os.path.join(root_dir, "ml", "artifacts", "product_embeddings.joblib")

    # Phase 7 — Cart Optimization Settings
    CART_MAX_STORES: int = 2
    CART_MIN_SPLIT_SAVING: float = 50.0
    CART_DEFAULT_DEMO_DELIVERY_FEE: float = 30.0

    # Swiggy Instamart MCP Integration Settings
    SWIGGY_INSTAMART_CLIENT_ID: Optional[str] = None
    SWIGGY_INSTAMART_CLIENT_SECRET: Optional[str] = None
    SWIGGY_INSTAMART_ACCESS_TOKEN: Optional[str] = None
    SWIGGY_INSTAMART_MCP_URL: Optional[str] = "https://mcp.swiggy.com/im"
    SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID: Optional[str] = "default_address"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        origins = [self.FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:5173"]
        return list(set(origins))


settings = Settings()
