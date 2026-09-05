from __future__ import annotations
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Settings:
    DISHIQ_BACKEND_URL: str = os.getenv("DISHIQ_BACKEND_URL", "http://127.0.0.1:8000/api")
    DISHIQ_REQUEST_TIMEOUT: float = float(os.getenv("DISHIQ_REQUEST_TIMEOUT", "10.0"))
    DISHIQ_MCP_SERVER_NAME: str = os.getenv("DISHIQ_MCP_SERVER_NAME", "DishIQ-MCP")
    DISHIQ_MCP_SERVER_VERSION: str = os.getenv("DISHIQ_MCP_SERVER_VERSION", "1.0.0")

settings = Settings()
