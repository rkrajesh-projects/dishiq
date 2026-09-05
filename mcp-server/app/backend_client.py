from __future__ import annotations
import httpx
from typing import Any, Dict, Optional
from app.config import settings
from app.errors import (
    BackendUnavailableError,
    RequestTimeoutError,
    BackendValidationFailureError,
    UnexpectedBackendResponseError,
)

class BackendClient:
    """
    Reusable backend client for communicating with the DishIQ FastAPI backend.
    
    Delegates all business logic and database queries to the backend API endpoints
    to avoid code duplication.
    """
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or settings.DISHIQ_BACKEND_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.DISHIQ_REQUEST_TIMEOUT

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, params=params, json=json)
            except httpx.ConnectError as e:
                raise BackendUnavailableError(f"Cannot reach DishIQ backend at {url}: {str(e)}")
            except httpx.TimeoutException as e:
                raise RequestTimeoutError(f"Connection to DishIQ backend timed out: {str(e)}")
            except httpx.RequestError as e:
                raise BackendUnavailableError(f"HTTP request failed: {str(e)}")

            # Handle response errors
            if response.status_code == 422:
                try:
                    detail = response.json().get("detail", "Validation failed")
                except Exception:
                    detail = response.text
                raise BackendValidationFailureError(f"Backend validation failed (422): {detail}")

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise BackendUnavailableError(f"Backend returned HTTP error {response.status_code}: {str(e)}")

            # Parse JSON safely
            try:
                return response.json()
            except ValueError as e:
                raise UnexpectedBackendResponseError(f"Failed to parse backend JSON response: {str(e)}")

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        return await self.request("POST", path, json=json)
