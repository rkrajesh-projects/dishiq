import pytest
import os
import json
import base64
import hashlib
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.grocery_sources.swiggy_oauth import SwiggyOAuthManager, SwiggyTokenStorage


class TestSwiggyOAuthPKCE:

    def test_pkce_generation(self):
        """Verify PKCE code_verifier and code_challenge match RFC 7636."""
        verifier, challenge = SwiggyOAuthManager.generate_pkce()

        assert len(verifier) >= 43
        assert len(verifier) <= 128
        assert "=" not in challenge

        # Manually compute expected challenge from verifier
        expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).decode("ascii").rstrip("=")

        assert challenge == expected_challenge

    @pytest.mark.asyncio
    async def test_create_authorization_url(self, tmp_path):
        """Verify authorization URL structure complies with Swiggy OAuth 2.1 specification."""
        storage = SwiggyTokenStorage(file_path=str(tmp_path / "tokens.json"))
        manager = SwiggyOAuthManager(token_storage=storage)

        with patch.object(settings, "SWIGGY_INSTAMART_CLIENT_ID", "test_client_id"):
            auth_url, state = await manager.create_authorization_url()

            assert auth_url.startswith("https://mcp.swiggy.com/auth/authorize")
            assert "client_id=test_client_id" in auth_url
            assert "response_type=code" in auth_url
            assert "code_challenge=" in auth_url
            assert f"state={state}" in auth_url
            assert "scope=mcp%3Atools" in auth_url or "scope=mcp:tools" in auth_url

            # Verify state was recorded in pending states
            assert state in manager._pending_states
            assert manager._pending_states[state]["code_verifier"] is not None

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_exchange_code_success(self, mock_post, tmp_path):
        """Verify successful code exchange stores tokens securely without leaking secrets."""
        storage = SwiggyTokenStorage(file_path=str(tmp_path / "tokens.json"))
        manager = SwiggyOAuthManager(token_storage=storage)

        # Seed pending state
        state = "valid_state_123"
        manager._pending_states[state] = {
            "code_verifier": "my_test_verifier",
            "redirect_uri": "http://localhost:8001/api/v1/swiggy/oauth/callback",
            "client_id": "client_abc",
            "timestamp": 9999999999,
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mock_jwt_access_token",
            "refresh_token": "mock_jwt_refresh_token",
            "token_type": "Bearer",
            "expires_in": 432000,
            "scope": "mcp:tools",
        }
        mock_post.return_value = mock_resp

        res = await manager.exchange_code(code="auth_code_xyz", state=state)

        assert res["status"] == "success"
        assert res["token_type"] == "Bearer"
        assert res["expires_in"] == 432000
        # Tokens must not be directly in return summary
        assert "access_token" not in res

        # Verify stored securely on disk
        stored = storage.load_tokens()
        assert stored is not None
        assert stored["access_token"] == "mock_jwt_access_token"
        assert stored["refresh_token"] == "mock_jwt_refresh_token"
        assert storage.is_authenticated() is True

        # Verify state is cleared to prevent replay attack
        assert state not in manager._pending_states

    @pytest.mark.asyncio
    async def test_exchange_code_invalid_state_rejected(self, tmp_path):
        """Verify mismatched or missing state raises CSRF validation error."""
        storage = SwiggyTokenStorage(file_path=str(tmp_path / "tokens.json"))
        manager = SwiggyOAuthManager(token_storage=storage)

        with pytest.raises(ValueError) as exc:
            await manager.exchange_code(code="code_123", state="unknown_state")
        assert "Invalid or expired OAuth state" in str(exc.value)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_refresh_token_rotation(self, mock_post, tmp_path):
        """Verify token refresh rotates the refresh_token and updates storage."""
        storage = SwiggyTokenStorage(file_path=str(tmp_path / "tokens.json"))
        storage.save_tokens(
            access_token="old_access_token",
            refresh_token="old_refresh_token",
            expires_in=100,
            client_id="client_abc",
        )
        manager = SwiggyOAuthManager(token_storage=storage)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "new_rotated_access",
            "refresh_token": "new_rotated_refresh",
            "token_type": "Bearer",
            "expires_in": 432000,
        }
        mock_post.return_value = mock_resp

        new_acc = await manager.refresh_tokens()
        assert new_acc == "new_rotated_access"

        stored = storage.load_tokens()
        assert stored["access_token"] == "new_rotated_access"
        assert stored["refresh_token"] == "new_rotated_refresh"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_refresh_token_without_rotation_preserves_existing_refresh_token(self, mock_post, tmp_path):
        """Verify token refresh without a new refresh_token in response preserves the existing refresh token."""
        storage = SwiggyTokenStorage(file_path=str(tmp_path / "tokens.json"))
        storage.save_tokens(
            access_token="old_access_token",
            refresh_token="original_persistent_refresh_token",
            expires_in=100,
            client_id="client_abc",
        )
        manager = SwiggyOAuthManager(token_storage=storage)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "new_access_token_only",
            "token_type": "Bearer",
            "expires_in": 432000,
        }
        mock_post.return_value = mock_resp

        new_acc = await manager.refresh_tokens()
        assert new_acc == "new_access_token_only"

        stored = storage.load_tokens()
        assert stored["access_token"] == "new_access_token_only"
        assert stored["refresh_token"] == "original_persistent_refresh_token"


class TestSwiggyAuthAPIRoutes:

    def test_status_endpoint(self, tmp_path):
        """Verify GET /api/v1/swiggy/status never exposes secrets."""
        client = TestClient(app)
        response = client.get("/api/v1/swiggy/status")
        assert response.status_code == 200
        data = response.json()
        assert "authenticated" in data
        assert "has_access_token" in data
        assert "has_refresh_token" in data
        assert "access_token" not in data
        assert "refresh_token" not in data

    @patch("app.grocery_sources.swiggy_oauth.swiggy_oauth_manager.create_authorization_url")
    def test_login_endpoint_json_mode(self, mock_create):
        """Verify GET /api/v1/swiggy/login?redirect=false returns auth URL."""
        async def fake_create():
            return "https://mcp.swiggy.com/auth/authorize?client_id=demo", "state123"
        mock_create.side_effect = fake_create

        client = TestClient(app)
        response = client.get("/api/v1/swiggy/login?redirect=false")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert data["state"] == "state123"

    @patch("app.grocery_sources.swiggy_oauth.swiggy_oauth_manager.exchange_code")
    def test_callback_endpoint_success(self, mock_exchange):
        """Verify callback HTML response on successful authorization."""
        async def fake_exchange(code, state):
            return {"status": "success"}
        mock_exchange.side_effect = fake_exchange

        client = TestClient(app)
        response = client.get("/api/v1/swiggy/oauth/callback?code=mock_code&state=mock_state")
        assert response.status_code == 200
        assert "Swiggy Instamart Connected!" in response.text


class TestSwiggyLogRedactionAndDCR:

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_dcr_fallback_when_client_id_is_dummy(self, mock_post, tmp_path):
        """Verify register_client_if_needed ignores dummy_id and performs DCR."""
        storage = SwiggyTokenStorage(file_path=str(tmp_path / "tokens.json"))
        manager = SwiggyOAuthManager(token_storage=storage)

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "client_id": "swiggy-mcp",
            "client_name": "DishIQ",
            "redirect_uris": ["http://localhost:8001/api/v1/swiggy/oauth/callback"],
        }
        mock_post.return_value = mock_resp

        with patch.object(settings, "SWIGGY_INSTAMART_CLIENT_ID", "dummy_id"):
            client_id = await manager.register_client_if_needed("http://localhost:8001/api/v1/swiggy/oauth/callback")
            assert client_id == "swiggy-mcp"
            assert mock_post.called

    def test_log_redaction_utility(self):
        """Verify sensitive OAuth query parameters are cleanly redacted from logs."""
        from app.core.logging import redact_sensitive_query_params

        sample_url = "http://localhost:8001/api/v1/swiggy/oauth/callback?code=super_secret_auth_code_999&state=random_anti_csrf_token_888&scope=mcp:tools"
        redacted = redact_sensitive_query_params(sample_url)

        assert "super_secret_auth_code_999" not in redacted
        assert "random_anti_csrf_token_888" not in redacted
        assert "code=[REDACTED]" in redacted
        assert "state=[REDACTED]" in redacted
        assert "scope=mcp:tools" in redacted

    def test_sensitive_data_filter_on_log_records(self):
        """Verify SensitiveDataFilter sanitizes log record messages and args."""
        import logging
        import io
        from app.core.logging import SensitiveDataFilter

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(SensitiveDataFilter())

        test_logger = logging.getLogger("test_redaction_logger")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)

        test_logger.info(
            "OAuth redirect received: %s with state: %s",
            "/callback?code=auth_code_to_hide&other=1",
            "state_param_to_hide",
        )

        output = stream.getvalue()
        assert "auth_code_to_hide" not in output
        assert "code=[REDACTED]" in output

    def test_status_has_default_address_flag(self):
        """Verify GET /api/v1/swiggy/status includes has_default_address boolean."""
        client = TestClient(app)
        with patch.object(settings, "SWIGGY_INSTAMART_DEFAULT_ADDRESS_ID", "addr_mock_123"):
            resp = client.get("/api/v1/swiggy/status")
            assert resp.status_code == 200
            data = resp.json()
            assert "has_default_address" in data
            assert data["has_default_address"] is True
            # Raw address ID string must never be returned in status
            assert "addr_mock_123" not in str(data)

    @pytest.mark.asyncio
    @patch("app.grocery_sources.swiggy_instamart_provider.SwiggyInstamartMcpProvider.get_addresses")
    async def test_list_addresses_sanitizes_phone(self, mock_get_addrs):
        """Verify GET /api/v1/swiggy/addresses masks private phone numbers."""
        client = TestClient(app)
        mock_get_addrs.return_value = [
            {
                "id": "addr_9988",
                "addressLine": "123 Test St",
                "phoneNumber": "9876543210",
                "addressCategory": "HOME",
            }
        ]

        with patch("app.grocery_sources.swiggy_instamart_provider.SwiggyInstamartMcpProvider.is_configured", True):
            resp = client.get("/api/v1/swiggy/addresses")
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] == 1
            addr = data["addresses"][0]
            assert addr["id"] == "addr_9988"
            assert addr["phoneNumber"] == "******3210"
            assert "9876543210" not in str(data)


