import os
import json
import time
import secrets
import hashlib
import base64
from urllib.parse import urlencode
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from app.core.config import settings


def is_valid_credential(val: Optional[str]) -> bool:
    """
    Check if a string is a non-empty, genuine credential and not a placeholder/dummy value.
    """
    if not val or not isinstance(val, str):
        return False
    cleaned = val.strip().lower()
    return cleaned not in (
        "",
        "dummy_id",
        "dummy_secret",
        "dummy",
        "placeholder",
        "none",
        "null",
        "default_address",
    )


class SwiggyTokenStorage:
    """
    Secure file-backed token store for official Swiggy Instamart OAuth 2.1 tokens.
    Persists tokens atomically to disk so session survives container restarts.
    Never exposes token strings in logs or debug messages.
    """

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or settings.SWIGGY_TOKEN_FILE_PATH
        self._cache: Optional[Dict[str, Any]] = None

    def _ensure_directory(self) -> None:
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def load_tokens(self) -> Optional[Dict[str, Any]]:
        """Load stored tokens from disk into memory cache."""
        if self._cache is not None:
            return self._cache

        if not os.path.exists(self.file_path):
            return None

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._cache = data
                    return data
        except Exception:
            return None
        return None

    def save_tokens(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        client_id: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> None:
        """
        Atomically save tokens to disk using .tmp file and os.replace
        to prevent partial writes or corruption.
        """
        self._ensure_directory()

        current = self.load_tokens() or {}
        now = time.time()
        expires_at = (now + expires_in) if expires_in else None

        # Determine best genuine client_id
        resolved_cid = client_id if is_valid_credential(client_id) else None
        if not resolved_cid:
            prev_cid = current.get("client_id")
            if is_valid_credential(prev_cid):
                resolved_cid = prev_cid
        if not resolved_cid and is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_ID):
            resolved_cid = settings.SWIGGY_INSTAMART_CLIENT_ID

        updated: Dict[str, Any] = {
            "client_id": resolved_cid or "swiggy-mcp",
            "access_token": access_token,
            "refresh_token": refresh_token or current.get("refresh_token"),
            "expires_at": expires_at,
            "scope": scope or current.get("scope") or "mcp:tools",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        temp_path = f"{self.file_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(updated, f, indent=2)
            os.replace(temp_path, self.file_path)
            self._cache = updated
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            raise RuntimeError(f"Failed to persist Swiggy OAuth tokens: {str(e)}")

    def save_client_id(self, client_id: str) -> None:
        """Save a dynamically registered client_id."""
        if not is_valid_credential(client_id):
            return
        self._ensure_directory()
        current = self.load_tokens() or {}
        current["client_id"] = client_id
        current["updated_at"] = datetime.now(timezone.utc).isoformat()

        temp_path = f"{self.file_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
            os.replace(temp_path, self.file_path)
            self._cache = current
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def get_access_token(self) -> Optional[str]:
        tokens = self.load_tokens()
        if tokens and tokens.get("access_token"):
            return tokens["access_token"]
        return None

    def get_refresh_token(self) -> Optional[str]:
        tokens = self.load_tokens()
        if tokens and tokens.get("refresh_token"):
            return tokens["refresh_token"]
        return None

    def get_client_id(self) -> Optional[str]:
        tokens = self.load_tokens()
        if tokens and is_valid_credential(tokens.get("client_id")):
            return tokens["client_id"]
        if is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_ID):
            return settings.SWIGGY_INSTAMART_CLIENT_ID
        return None

    def is_authenticated(self) -> bool:
        """Check if an access token or refresh token is available."""
        tokens = self.load_tokens()
        if not tokens:
            return False
        return bool(tokens.get("access_token") or tokens.get("refresh_token"))

    def is_expired(self) -> bool:
        """Check if the current access token has expired."""
        tokens = self.load_tokens()
        if not tokens or not tokens.get("expires_at"):
            return False
        # Consider expired if within 60 seconds of expiration
        return time.time() >= (tokens["expires_at"] - 60)

    def clear(self) -> None:
        """Clear tokens and remove cache file."""
        self._cache = None
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception:
                pass


class SwiggyOAuthManager:
    """
    Manages OAuth 2.1 + PKCE authentication flow for Swiggy Instamart MCP Server.
    Complies with RFC 7636 (PKCE), RFC 7591 (Dynamic Client Registration),
    and Swiggy official Builders Club authentication specification.
    """

    def __init__(self, token_storage: Optional[SwiggyTokenStorage] = None):
        self.storage = token_storage or SwiggyTokenStorage()
        # Pending OAuth states: state -> {code_verifier, redirect_uri, client_id, timestamp}
        self._pending_states: Dict[str, Dict[str, Any]] = {}
        self._state_ttl_seconds = 900  # 15 minutes

    def _clean_expired_states(self) -> None:
        now = time.time()
        expired = [s for s, data in self._pending_states.items() if now - data.get("timestamp", 0) > self._state_ttl_seconds]
        for s in expired:
            del self._pending_states[s]

    @staticmethod
    def generate_pkce() -> Tuple[str, str]:
        """
        Generate RFC 7636 PKCE code_verifier and code_challenge using S256 method.
        Verifier: 64 random bytes urlsafe (min 43, max 128 chars).
        Challenge: base64url(SHA256(verifier)) unpadded.
        """
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return code_verifier, code_challenge

    async def register_client_if_needed(self, redirect_uri: str) -> str:
        """
        Ensure a client_id is available.
        Checks settings, then token storage cache, then attempts Dynamic Client Registration (RFC 7591).
        Never returns dummy/placeholder values.
        """
        # 1. Configured client_id (must be a genuine, non-placeholder ID)
        if is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_ID):
            return settings.SWIGGY_INSTAMART_CLIENT_ID

        # 2. Cached client_id from earlier DCR
        cached_id = self.storage.get_client_id()
        if is_valid_credential(cached_id):
            return cached_id

        # 3. Dynamic Client Registration (RFC 7591)
        register_url = settings.SWIGGY_INSTAMART_REGISTER_URL or "https://mcp.swiggy.com/auth/register"
        registration_payload = {
            "client_name": "DishIQ",
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "mcp:tools",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    register_url,
                    json=registration_payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    cid = data.get("client_id")
                    if cid:
                        self.storage.save_client_id(cid)
                        return cid
                # If DCR returns an error, raise with clear context
                detail = resp.text
                try:
                    detail = resp.json().get("error_description") or resp.json().get("message") or resp.text
                except Exception:
                    pass
                raise RuntimeError(
                    f"Swiggy Dynamic Client Registration returned HTTP {resp.status_code}: {detail}. "
                    "If Swiggy requires allowlisting or a static client_id, configure SWIGGY_INSTAMART_CLIENT_ID in your .env."
                )
        except httpx.HTTPError as e:
            raise RuntimeError(
                f"Failed to reach Swiggy Dynamic Client Registration endpoint ({register_url}): {str(e)}. "
                "Configure SWIGGY_INSTAMART_CLIENT_ID in your .env if using a pre-registered client."
            )

    async def create_authorization_url(self, redirect_uri: Optional[str] = None) -> Tuple[str, str]:
        """
        Create official Swiggy authorization URL with PKCE S256 parameters.
        Returns:
            (authorization_url, state)
        """
        self._clean_expired_states()

        r_uri = redirect_uri or settings.SWIGGY_INSTAMART_REDIRECT_URI
        client_id = await self.register_client_if_needed(r_uri)

        code_verifier, code_challenge = self.generate_pkce()
        state = secrets.token_urlsafe(32)

        self._pending_states[state] = {
            "code_verifier": code_verifier,
            "redirect_uri": r_uri,
            "client_id": client_id,
            "timestamp": time.time(),
        }

        auth_base = settings.SWIGGY_INSTAMART_AUTHORIZE_URL or "https://mcp.swiggy.com/auth/authorize"
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": r_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "scope": "mcp:tools",
        }
        query_string = urlencode(params)
        auth_url = f"{auth_base}?{query_string}"

        return auth_url, state

    async def exchange_code(self, code: str, state: str) -> Dict[str, Any]:
        """
        Exchange authorization code + PKCE code_verifier for access and refresh tokens.
        Validates state to prevent CSRF.
        """
        self._clean_expired_states()

        if state not in self._pending_states:
            raise ValueError("Invalid or expired OAuth state parameter. Please restart authorization.")

        state_data = self._pending_states.pop(state)
        code_verifier = state_data["code_verifier"]
        redirect_uri = state_data["redirect_uri"]
        client_id = state_data["client_id"]

        token_url = settings.SWIGGY_INSTAMART_AUTH_URL or "https://mcp.swiggy.com/auth/token"
        body = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "client_id": client_id if is_valid_credential(client_id) else "swiggy-mcp",
        }
        if is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_SECRET):
            body["client_secret"] = settings.SWIGGY_INSTAMART_CLIENT_SECRET

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    token_url,
                    json=body,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                if resp.status_code != 200:
                    err_msg = f"Token exchange failed (HTTP {resp.status_code})"
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("error_description") or err_json.get("error") or err_msg
                    except Exception:
                        pass
                    raise RuntimeError(f"Swiggy authorization exchange error: {err_msg}")

                data = resp.json()
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                expires_in = data.get("expires_in")
                scope = data.get("scope")

                if not access_token:
                    raise RuntimeError("Swiggy token endpoint did not return an access_token.")

                # Persist securely without printing secrets
                self.storage.save_tokens(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=expires_in,
                    client_id=client_id if is_valid_credential(client_id) else "swiggy-mcp",
                    scope=scope,
                )

                return {
                    "status": "success",
                    "token_type": data.get("token_type", "Bearer"),
                    "expires_in": expires_in,
                    "scope": scope,
                }
        except httpx.HTTPError as e:
            raise RuntimeError(f"Network error communicating with Swiggy token endpoint: {str(e)}")

    async def refresh_tokens(self) -> Optional[str]:
        """
        Refresh access token using stored refresh_token.
        Rotates refresh token upon successful response.
        """
        ref_tok = self.storage.get_refresh_token()
        if not is_valid_credential(ref_tok):
            ref_tok = (
                settings.SWIGGY_INSTAMART_REFRESH_TOKEN
                if is_valid_credential(settings.SWIGGY_INSTAMART_REFRESH_TOKEN)
                else None
            )
        if not ref_tok:
            return None

        client_id = self.storage.get_client_id()
        if not is_valid_credential(client_id):
            client_id = (
                settings.SWIGGY_INSTAMART_CLIENT_ID
                if is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_ID)
                else "swiggy-mcp"
            )

        token_url = settings.SWIGGY_INSTAMART_AUTH_URL or "https://mcp.swiggy.com/auth/token"

        body = {
            "grant_type": "refresh_token",
            "refresh_token": ref_tok,
        }
        if client_id and is_valid_credential(client_id):
            body["client_id"] = client_id
        if is_valid_credential(settings.SWIGGY_INSTAMART_CLIENT_SECRET):
            body["client_secret"] = settings.SWIGGY_INSTAMART_CLIENT_SECRET

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    token_url,
                    json=body,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    new_acc = data.get("access_token")
                    new_ref = data.get("refresh_token")
                    expires_in = data.get("expires_in")

                    if new_acc:
                        self.storage.save_tokens(
                            access_token=new_acc,
                            refresh_token=new_ref or ref_tok,
                            expires_in=expires_in,
                            client_id=client_id,
                            scope=data.get("scope"),
                        )
                        return new_acc
                elif resp.status_code in (400, 401):
                    # Refresh token is revoked or expired
                    pass
        except Exception:
            pass
        return None


# Global singletons
swiggy_token_storage = SwiggyTokenStorage()
swiggy_oauth_manager = SwiggyOAuthManager(swiggy_token_storage)
