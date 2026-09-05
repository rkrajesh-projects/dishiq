import pytest
import httpx
from app.config import settings
from app.backend_client import BackendClient
from app.errors import (
    BackendUnavailableError,
    RequestTimeoutError,
    BackendValidationFailureError,
)
from app.server import server, list_tools_handler, call_tool_handler
import mcp_types as types


def test_config_loads_correctly():
    """Verify that environment settings load correctly."""
    assert settings.DISHIQ_MCP_SERVER_NAME is not None
    assert settings.DISHIQ_MCP_SERVER_VERSION is not None
    assert "api" in settings.DISHIQ_BACKEND_URL


def test_backend_client_url_construction():
    """Verify client constructs the correct request URL."""
    client = BackendClient(base_url="http://test-url/api", timeout=5.0)
    assert client.base_url == "http://test-url/api"
    assert client.timeout == 5.0


@pytest.mark.asyncio
async def test_backend_connection_error_handled(mocker):
    """Verify ConnectError is mapped to BackendUnavailableError."""
    client = BackendClient(base_url="http://test-url/api")
    mocker.patch("httpx.AsyncClient.request", side_effect=httpx.ConnectError("Connection refused"))
    
    with pytest.raises(BackendUnavailableError) as exc_info:
        await client.get("/health")
    assert "Cannot reach DishIQ backend" in str(exc_info.value)


@pytest.mark.asyncio
async def test_backend_timeout_handled(mocker):
    """Verify TimeoutException is mapped to RequestTimeoutError."""
    client = BackendClient(base_url="http://test-url/api")
    mocker.patch("httpx.AsyncClient.request", side_effect=httpx.TimeoutException("Timed out"))
    
    with pytest.raises(RequestTimeoutError) as exc_info:
        await client.get("/health")
    assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_backend_validation_error_handled(mocker):
    """Verify HTTP 422 yields BackendValidationFailureError."""
    client = BackendClient(base_url="http://test-url/api")
    
    mock_response = mocker.Mock()
    mock_response.status_code = 422
    mock_response.json.return_value = {"detail": "Invalid quantity"}
    mocker.patch("httpx.AsyncClient.request", return_value=mock_response)
    
    with pytest.raises(BackendValidationFailureError) as exc_info:
        await client.get("/health")
    assert "Invalid quantity" in str(exc_info.value)


@pytest.mark.asyncio
async def test_mcp_server_tool_listing():
    """Verify tools handler reports configured tool metadata."""
    res = await list_tools_handler(None, None)
    assert isinstance(res, types.ListToolsResult)
    assert len(res.tools) == 10
    assert res.tools[0].name == "health"


@pytest.mark.asyncio
async def test_mcp_server_health_tool_execution_success(mocker):
    """Verify health tool executes successfully when backend is online."""
    mocker.patch("app.backend_client.BackendClient.get", return_value={"status": "ok"})
    
    params = types.CallToolRequestParams(name="health", arguments={})
    res = await call_tool_handler(None, params)
    
    assert isinstance(res, types.CallToolResult)
    assert len(res.content) == 1
    assert "Connected to DishIQ Backend successfully" in res.content[0].text


@pytest.mark.asyncio
async def test_mcp_server_health_tool_execution_failure(mocker):
    """Verify health tool reports backend failure gracefully."""
    mocker.patch(
        "app.backend_client.BackendClient.get",
        side_effect=BackendUnavailableError("Service offline")
    )
    
    params = types.CallToolRequestParams(name="health", arguments={})
    res = await call_tool_handler(None, params)
    
    assert isinstance(res, types.CallToolResult)
    assert len(res.content) == 1
    assert "health check failed: Service offline" in res.content[0].text


@pytest.mark.asyncio
async def test_mcp_server_invalid_tool():
    """Verify calling an unregistered tool returns an error message."""
    params = types.CallToolRequestParams(name="non_existent_tool", arguments={})
    res = await call_tool_handler(None, params)
    
    assert isinstance(res, types.CallToolResult)
    assert res.is_error is True
    assert "not found" in res.content[0].text
