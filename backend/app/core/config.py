import os
import sys
from typing import Any, List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

def _find_project_root() -> str:
    # 1. Environment variable override if specified
    if "PROJECT_ROOT" in os.environ and os.path.exists(os.environ["PROJECT_ROOT"]):
        return os.path.abspath(os.environ["PROJECT_ROOT"])
    # 2. Check container layout: /app containing ml/artifacts
    candidate_app = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if os.path.exists(os.path.join(candidate_app, "ml", "artifacts")):
        return candidate_app
    # 3. Check host layout: repo_root containing ml/artifacts
    candidate_host = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if os.path.exists(os.path.join(candidate_host, "ml", "artifacts")):
        return candidate_host
    return candidate_host

# Ensure project root is in sys.path for shared imports like `ml`
root_dir = _find_project_root()
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class Settings(BaseSettings):
    APP_NAME: str = "DishIQ"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Authentication / JWT Settings
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "DishIQ_Super_Secret_Key_Change_In_Production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    DATABASE_URL: str = "sqlite:///./dishiq.db"
    LOG_LEVEL: str = "INFO"
    FRONTEND_URL: str = "http://localhost:5173"
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    PRODUCT_MATCH_THRESHOLD: float = 0.40
    PRODUCT_EMBEDDINGS_ARTIFACT_PATH: str = os.path.join(
        root_dir, "ml", "artifacts", "product_embeddings.joblib"
    )

    # Phase 7 — Cart Optimization Settings
    CART_MAX_STORES: int = 2
    CART_MIN_SPLIT_SAVING: float = 50.0
    CART_DEFAULT_DEMO_DELIVERY_FEE: float = 30.0
    CART_OPTIMIZATION_CONCURRENCY: int = 4

    # Swiggy Instamart MCP Integration Settings
    SWIGGY_INSTAMART_CLIENT_ID: Optional[str] = None
    SWIGGY_INSTAMART_CLIENT_SECRET: Optional[str] = None
    SWIGGY_INSTAMART_ACCESS_TOKEN: Optional[str] = None
    SWIGGY_INSTAMART_REFRESH_TOKEN: Optional[str] = None
    SWIGGY_INSTAMART_AUTH_URL: Optional[str] = "https://mcp.swiggy.com/auth/token"
    SWIGGY_INSTAMART_AUTHORIZE_URL: str = "https://mcp.swiggy.com/auth/authorize"
    SWIGGY_INSTAMART_REGISTER_URL: str = "https://mcp.swiggy.com/auth/register"
    SWIGGY_INSTAMART_REDIRECT_URI: str = "http://localhost:8001/api/v1/swiggy/oauth/callback"
    SWIGGY_TOKEN_FILE_PATH: str = os.path.join(
        root_dir, "ml", "artifacts", "swiggy_oauth_tokens.json"
    )
    SWIGGY_INSTAMART_MCP_URL: Optional[str] = "https://mcp.swiggy.com/im"
    SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID: Optional[str] = None
    SWIGGY_INSTAMART_LATITUDE: Optional[float] = None
    SWIGGY_INSTAMART_LONGITUDE: Optional[float] = None
    SWIGGY_INSTAMART_TIMEOUT_SECONDS: float = 4.0

    @field_validator("SWIGGY_INSTAMART_LATITUDE", "SWIGGY_INSTAMART_LONGITUDE", mode="before")
    @classmethod
    def parse_optional_coordinate(cls, v: Any) -> Optional[float]:
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return float(v)

    # QuickCommerce Provider API config
    GROCERY_PROVIDER: str = "demo"
    QUICKCOMMERCE_API_KEY: Optional[str] = None
    QUICKCOMMERCE_API_URL: Optional[str] = (
        "https://api.quickcommerce-aggregator.com/v1/search"
    )
    DEFAULT_PINCODE: str = "600016"
    GROCERY_CACHE_TTL_SECONDS: int = 300
    GROCERY_CACHE_STALE_TTL_SECONDS: int = 1800
    GROCERY_SEARCH_TIMEOUT_SECONDS: float = 4.0

    # Phase 12 — AI Cooking Companion Settings
    AI_PROVIDER: str = "demo"
    AI_API_KEY: Optional[str] = None
    AI_API_URL: Optional[str] = None
    AI_MODEL: Optional[str] = "gemini-1.5-flash"
    AI_TIMEOUT_SECONDS: int = 10
    AI_MAX_CONTEXT_MESSAGES: int = 8
    AI_MAX_MESSAGE_LENGTH: int = 1000

    model_config = SettingsConfigDict(
        env_file=(os.path.join(root_dir, ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        origins = [
            self.FRONTEND_URL,
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]
        return list(set(origins))


settings = Settings()