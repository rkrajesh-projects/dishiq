from __future__ import annotations
class MCPBaseError(Exception):
    """Base exception for all MCP foundation errors."""
    def __init__(self, message: str, code: int = -32603):
        super().__init__(message)
        self.message = message
        self.code = code


class BackendUnavailableError(MCPBaseError):
    """Raised when the DishIQ FastAPI backend cannot be reached."""
    def __init__(self, message: str = "The DishIQ backend is currently unavailable."):
        super().__init__(message, code=-32001)


class RequestTimeoutError(MCPBaseError):
    """Raised when requests to the DishIQ backend time out."""
    def __init__(self, message: str = "Request to the DishIQ backend timed out."):
        super().__init__(message, code=-32002)


class InvalidToolInputError(MCPBaseError):
    """Raised when tool parameters do not validate."""
    def __init__(self, message: str = "Invalid tool input parameters provided."):
        super().__init__(message, code=-32602)


class BackendValidationFailureError(MCPBaseError):
    """Raised when the backend returns validation errors (422 HTTP)."""
    def __init__(self, message: str = "Backend validation failure."):
        super().__init__(message, code=-32003)


class UnexpectedBackendResponseError(MCPBaseError):
    """Raised when the backend returns unexpected response schemas or data formats."""
    def __init__(self, message: str = "Received an unexpected response format from the backend."):
        super().__init__(message, code=-32004)
