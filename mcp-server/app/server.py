from __future__ import annotations
import asyncio
import logging
from typing import Any
import mcp.types as types
from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from app.config import settings
from app.backend_client import BackendClient
from app.errors import MCPBaseError
from app.tools.recipes import (
    get_recipe_tools,
    execute_search_recipes,
    execute_get_recipe,
    execute_get_recipe_ingredients,
)
from app.tools.grocery import (
    get_grocery_tools,
    execute_search_grocery_products,
    execute_compare_recipe_cart,
    execute_get_store_prices,
)
from app.tools.pantry import (
    get_pantry_tools,
    execute_get_pantry,
    execute_check_missing_ingredients,
    execute_update_pantry,
)

# Configure logging to stderr so stdio JSON-RPC isn't corrupted
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

# Initialize backend client
backend_client = BackendClient()

async def list_tools_handler(
    ctx: Any,
    params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    """
    List all available tools.
    """
    logger.info("Listing tools")
    # Base health tool
    tools = [
        types.Tool(
            name="health",
            description="Perform a foundation connection check with the DishIQ backend.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        )
    ]
    # Add recipe tools
    tools.extend(get_recipe_tools())
    # Add grocery tools
    tools.extend(get_grocery_tools())
    # Add pantry tools
    tools.extend(get_pantry_tools())
    return types.ListToolsResult(tools=tools)


async def call_tool_handler(
    ctx: Any,
    params: types.CallToolRequestParams
) -> types.CallToolResult | types.InputRequiredResult:
    """
    Call a registered tool by name.
    """
    tool_name = params.name
    logger.info(f"Calling tool: {tool_name}")

    if tool_name == "health":
        try:
            # Reuses backend business logic via /health endpoint check
            backend_health = await backend_client.get("/health")
            status = backend_health.get("status", "unknown")
            msg = f"MCP server health check: Connected to DishIQ Backend successfully. Status: {status}"
        except MCPBaseError as e:
            msg = f"MCP server health check failed: {e.message} (Code: {e.code})"
        except Exception as e:
            msg = f"MCP server health check failed with unexpected error: {str(e)}"
            
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=msg
                )
            ]
        )
    elif tool_name == "search_recipes":
        try:
            return await execute_search_recipes(params.arguments or {})
        except MCPBaseError as e:
            return types.CallToolResult(
                is_error=True,
                content=[types.TextContent(type="text", text=e.message)]
            )
    elif tool_name == "get_recipe":
        try:
            return await execute_get_recipe(params.arguments or {})
        except MCPBaseError as e:
            return types.CallToolResult(
                is_error=True,
                content=[types.TextContent(type="text", text=e.message)]
            )
    elif tool_name == "get_recipe_ingredients":
        try:
            return await execute_get_recipe_ingredients(params.arguments or {})
        except MCPBaseError as e:
            return types.CallToolResult(
                is_error=True,
                content=[types.TextContent(type="text", text=e.message)]
            )
    elif tool_name == "search_grocery_products":
        try:
            return await execute_search_grocery_products(params.arguments or {})
        except MCPBaseError as e:
            return types.CallToolResult(
                is_error=True,
                content=[types.TextContent(type="text", text=e.message)]
            )
    elif tool_name == "compare_recipe_cart":
        try:
            return await execute_compare_recipe_cart(params.arguments or {})
        except MCPBaseError as e:
            return types.CallToolResult(
                is_error=True,
                content=[types.TextContent(type="text", text=e.message)]
            )
    elif tool_name == "get_store_prices":
        try:
            return await execute_get_store_prices(params.arguments or {})
        except MCPBaseError as e:
            return types.CallToolResult(
                is_error=True,
                content=[types.TextContent(type="text", text=e.message)]
            )
    elif tool_name == "get_pantry":
        try:
            return await execute_get_pantry(params.arguments or {})
        except MCPBaseError as e:
            return types.CallToolResult(
                is_error=True,
                content=[types.TextContent(type="text", text=e.message)]
            )
    elif tool_name == "check_missing_ingredients":
        try:
            return await execute_check_missing_ingredients(params.arguments or {})
        except MCPBaseError as e:
            return types.CallToolResult(
                is_error=True,
                content=[types.TextContent(type="text", text=e.message)]
            )
    elif tool_name == "update_pantry":
        try:
            return await execute_update_pantry(params.arguments or {})
        except MCPBaseError as e:
            return types.CallToolResult(
                is_error=True,
                content=[types.TextContent(type="text", text=e.message)]
            )
    else:
        # Structured error return for method not found
        return types.CallToolResult(
            is_error=True,
            content=[
                types.TextContent(
                    type="text",
                    text=f"Tool '{tool_name}' not found."
                )
            ]
        )


# Construct server with metadata and handlers
server = Server(
    name=settings.DISHIQ_MCP_SERVER_NAME,
    version=settings.DISHIQ_MCP_SERVER_VERSION,
    description="Model Context Protocol server for DishIQ kitchen manager.",
    on_list_tools=list_tools_handler,
    on_call_tool=call_tool_handler,
)


async def run_server():
    """
    Run the MCP server over stdio transport.
    """
    logger.info(f"Starting MCP server: {settings.DISHIQ_MCP_SERVER_NAME} v{settings.DISHIQ_MCP_SERVER_VERSION}")
    
    init_options = InitializationOptions(
        server_name=settings.DISHIQ_MCP_SERVER_NAME,
        server_version=settings.DISHIQ_MCP_SERVER_VERSION,
        capabilities=types.ServerCapabilities(
            tools=types.ToolsCapability()
        )
    )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            init_options,
        )




if __name__ == "__main__":
    asyncio.run(run_server())
