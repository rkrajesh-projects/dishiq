"""
FastAPI router for Swiggy Instamart MCP OAuth 2.1 + PKCE authentication flow.
Handles login initiation, callback code exchange, status checks, and session cleanup.
Never exposes token secrets, OTPs, or private credentials to users or frontend.
"""
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Any, Dict, Optional

from app.grocery_sources.swiggy_oauth import swiggy_oauth_manager, swiggy_token_storage, is_valid_credential
from app.core.config import settings

router = APIRouter(prefix="/swiggy", tags=["Swiggy MCP Authentication"])


@router.get("/status", summary="Check Swiggy Instamart Authentication Status")
def get_auth_status() -> Dict[str, Any]:
    """
    Returns public authentication status for Swiggy Instamart MCP integration.
    Never exposes access or refresh token values or dummy placeholder client IDs.
    """
    tokens = swiggy_token_storage.load_tokens() or {}
    has_access = bool(
        swiggy_token_storage.get_access_token()
        or (settings.SWIGGY_INSTAMART_ACCESS_TOKEN if is_valid_credential(settings.SWIGGY_INSTAMART_ACCESS_TOKEN) else None)
    )
    has_refresh = bool(
        swiggy_token_storage.get_refresh_token()
        or (settings.SWIGGY_INSTAMART_REFRESH_TOKEN if is_valid_credential(settings.SWIGGY_INSTAMART_REFRESH_TOKEN) else None)
    )
    
    cid = swiggy_token_storage.get_client_id()
    if not is_valid_credential(cid):
        cid = (
            settings.SWIGGY_INSTAMART_CLIENT_ID
            if is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_ID)
            else "swiggy-mcp"
        )

    return {
        "authenticated": has_access or has_refresh,
        "has_access_token": has_access,
        "has_refresh_token": has_refresh,
        "client_id": cid,
        "is_expired": swiggy_token_storage.is_expired(),
        "scope": tokens.get("scope", "mcp:tools"),
        "updated_at": tokens.get("updated_at"),
        "latitude": settings.SWIGGY_INSTAMART_LATITUDE,
        "longitude": settings.SWIGGY_INSTAMART_LONGITUDE,
        "has_default_address": bool(settings.SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID),
    }


@router.get("/login", summary="Initiate Swiggy Instamart OAuth Login")
async def initiate_login(
    redirect: bool = Query(True, description="Redirect browser directly to Swiggy consent screen if True")
) -> Any:
    """
    Generates PKCE S256 parameters and constructs the official Swiggy authorization URL.
    """
    try:
        auth_url, state = await swiggy_oauth_manager.create_authorization_url()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Swiggy authorization: {str(e)}"
        )

    if redirect:
        return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    return {
        "authorization_url": auth_url,
        "state": state,
        "message": "Open the authorization_url in a browser to complete mobile + OTP verification on Swiggy.",
    }


@router.get("/oauth/callback", summary="OAuth 2.1 Redirect Callback Receiver", response_class=HTMLResponse)
async def oauth_callback(
    code: Optional[str] = Query(None, description="OAuth authorization code from Swiggy"),
    state: Optional[str] = Query(None, description="Anti-CSRF state token"),
    error: Optional[str] = Query(None, description="OAuth error code"),
    error_description: Optional[str] = Query(None, description="OAuth error description"),
) -> HTMLResponse:
    """
    Handles redirect callback from Swiggy consent UI, exchanges code with PKCE verifier,
    and stores session tokens securely.
    """
    if error:
        err_msg = error_description or error
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>DishIQ - Swiggy Connection Failed</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h2 style="color: #d32f2f;">Swiggy Authorization Error</h2>
                <p>Swiggy returned error: <strong>{err_msg}</strong></p>
                <p>You can close this tab and try again from DishIQ.</p>
            </body>
            </html>
            """,
            status_code=400,
        )

    if not code or not state:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head><title>DishIQ - Missing Parameters</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h2 style="color: #d32f2f;">Invalid Callback Request</h2>
                <p>Missing required authorization code or state parameter.</p>
            </body>
            </html>
            """,
            status_code=400,
        )

    try:
        await swiggy_oauth_manager.exchange_code(code=code, state=state)
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>DishIQ - Swiggy Instamart Connected</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
            </head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f7f9fa; color: #1a1a1a; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
                <div style="background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 40px; max-width: 480px; text-align: center;">
                    <div style="font-size: 48px; color: #2e7d32; margin-bottom: 16px;">&#10004;</div>
                    <h2 style="margin: 0 0 12px; color: #111;">Swiggy Instamart Connected!</h2>
                    <p style="color: #555; line-height: 1.5; margin-bottom: 24px;">
                        Your session has been securely authorized via OAuth 2.1 with PKCE. DishIQ can now perform real-time grocery product searches.
                    </p>
                    <p style="color: #888; font-size: 14px;">
                        You may now close this browser tab and return to DishIQ.
                    </p>
                </div>
            </body>
            </html>
            """,
            status_code=200,
        )
    except Exception as e:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>DishIQ - Exchange Failed</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h2 style="color: #d32f2f;">Token Exchange Failed</h2>
                <p>{str(e)}</p>
                <p>Please restart the authorization process.</p>
            </body>
            </html>
            """,
            status_code=500,
        )


@router.post("/logout", summary="Disconnect Swiggy Instamart Session")
def logout() -> Dict[str, str]:
    """
    Clears all saved Swiggy Instamart session tokens.
    """
    swiggy_token_storage.clear()
    return {"status": "logged_out", "message": "Swiggy Instamart session tokens have been cleared."}


@router.get("/addresses", summary="List Saved Addresses from Swiggy Instamart")
async def list_addresses() -> Dict[str, Any]:
    """
    Fetch saved addresses from Swiggy Instamart for the authenticated account.
    Phone numbers are partially masked to protect user privacy.
    """
    from app.grocery_sources.swiggy_instamart_provider import SwiggyInstamartMcpProvider

    provider = SwiggyInstamartMcpProvider()
    if not provider.is_configured:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Swiggy Instamart is not authenticated."
        )

    addresses = await provider.get_addresses()
    sanitized_addresses = []
    for addr in addresses:
        if isinstance(addr, dict):
            item = dict(addr)
            phone = item.get("phoneNumber") or item.get("phone")
            if phone and isinstance(phone, str) and len(phone) >= 4:
                item["phoneNumber"] = f"{'*' * (len(phone) - 4)}{phone[-4:]}"
            sanitized_addresses.append(item)

    return {
        "count": len(sanitized_addresses),
        "addresses": sanitized_addresses,
    }

