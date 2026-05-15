"""
Tests for the OAuth authentication provider and mcp_instance wiring.
"""

import os
import sys
import pathlib
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")


def _fresh_mcp(monkeypatch, client_id=None, client_secret=None):
    """Reimport mcp_instance with a clean module cache and given credentials."""
    if client_id is not None:
        monkeypatch.setenv("MCP_CLIENT_ID", client_id)
    else:
        monkeypatch.delenv("MCP_CLIENT_ID", raising=False)

    if client_secret is not None:
        monkeypatch.setenv("MCP_CLIENT_SECRET", client_secret)
    else:
        monkeypatch.delenv("MCP_CLIENT_SECRET", raising=False)

    for key in list(sys.modules.keys()):
        if "intervals_mcp_server" in key:
            del sys.modules[key]

    import intervals_mcp_server.mcp_instance as inst  # pylint: disable=import-outside-toplevel

    return inst


class TestSingleClientOAuthProvider:
    @pytest.mark.asyncio
    async def test_get_client_returns_none_for_unknown_id(self):
        from intervals_mcp_server.auth import SingleClientOAuthProvider  # pylint: disable=import-outside-toplevel

        provider = SingleClientOAuthProvider("myclient", "mysecret")
        result = await provider.get_client("unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_client_returns_client_for_registered_id(self):
        from intervals_mcp_server.auth import SingleClientOAuthProvider  # pylint: disable=import-outside-toplevel

        provider = SingleClientOAuthProvider("myclient", "mysecret")
        client = await provider.get_client("myclient")
        assert client is not None
        assert client.client_id == "myclient"
        assert client.client_secret == "mysecret"

    @pytest.mark.asyncio
    async def test_client_accepts_any_redirect_uri(self):
        from intervals_mcp_server.auth import SingleClientOAuthProvider  # pylint: disable=import-outside-toplevel
        from pydantic import AnyUrl  # pylint: disable=import-outside-toplevel

        provider = SingleClientOAuthProvider("myclient", "mysecret")
        client = await provider.get_client("myclient")
        assert client is not None
        redirect = AnyUrl("https://claude.ai/oauth/callback")
        assert client.validate_redirect_uri(redirect) == redirect

    @pytest.mark.asyncio
    async def test_load_access_token_accepts_correct_secret(self):
        from intervals_mcp_server.auth import SingleClientOAuthProvider  # pylint: disable=import-outside-toplevel

        provider = SingleClientOAuthProvider("myclient", "mysecret")
        result = await provider.load_access_token("mysecret")
        assert result is not None
        assert result.client_id == "myclient"

    @pytest.mark.asyncio
    async def test_load_access_token_rejects_wrong_token(self):
        from intervals_mcp_server.auth import SingleClientOAuthProvider  # pylint: disable=import-outside-toplevel

        provider = SingleClientOAuthProvider("myclient", "mysecret")
        result = await provider.load_access_token("wrong")
        assert result is None

    @pytest.mark.asyncio
    async def test_authorization_code_flow(self):
        from intervals_mcp_server.auth import SingleClientOAuthProvider  # pylint: disable=import-outside-toplevel
        from pydantic import AnyUrl  # pylint: disable=import-outside-toplevel
        from mcp.server.auth.provider import AuthorizationParams  # pylint: disable=import-outside-toplevel

        provider = SingleClientOAuthProvider("myclient", "mysecret")
        client = await provider.get_client("myclient")
        assert client is not None

        redirect_uri = AnyUrl("https://claude.ai/oauth/callback")
        params = AuthorizationParams(
            state="st",
            scopes=None,
            code_challenge="abc123",
            redirect_uri=redirect_uri,
            redirect_uri_provided_explicitly=True,
        )
        redirect_url = await provider.authorize(client, params)
        assert "code=" in redirect_url
        assert "state=st" in redirect_url

        # Extract the code from the redirect URL
        code = redirect_url.split("code=")[1].split("&")[0]
        auth_code = await provider.load_authorization_code(client, code)
        assert auth_code is not None
        assert auth_code.code_challenge == "abc123"

        token = await provider.exchange_authorization_code(client, auth_code)
        assert token.access_token == "mysecret"
        assert token.token_type.lower() == "bearer"

        # Code must be consumed after exchange
        assert await provider.load_authorization_code(client, code) is None

    @pytest.mark.asyncio
    async def test_expired_authorization_code_rejected(self):
        from intervals_mcp_server.auth import SingleClientOAuthProvider, _AuthCode  # pylint: disable=import-outside-toplevel
        from pydantic import AnyUrl  # pylint: disable=import-outside-toplevel

        provider = SingleClientOAuthProvider("myclient", "mysecret")
        expired_code = _AuthCode(
            code="expiredcode",
            client_id="myclient",
            redirect_uri="https://claude.ai/oauth/callback",
            redirect_uri_provided_explicitly=True,
            code_challenge="abc",
            expires_at=time.time() - 1,  # already expired
        )
        provider._codes["expiredcode"] = expired_code  # pylint: disable=protected-access

        client = await provider.get_client("myclient")
        result = await provider.load_authorization_code(client, "expiredcode")  # type: ignore[arg-type]
        assert result is None


class TestMcpInstanceAuth:
    def test_no_auth_when_credentials_unset(self, monkeypatch):
        inst = _fresh_mcp(monkeypatch)
        assert inst._auth_server_provider is None
        assert inst._auth_settings is None

    def test_auth_enabled_when_credentials_set(self, monkeypatch):
        inst = _fresh_mcp(monkeypatch, client_id="cid", client_secret="csecret")
        assert inst._auth_server_provider is not None
        assert inst._auth_settings is not None

    def test_auth_disabled_when_only_client_id_set(self, monkeypatch):
        inst = _fresh_mcp(monkeypatch, client_id="cid", client_secret=None)
        assert inst._auth_server_provider is None

    def test_auth_disabled_when_only_client_secret_set(self, monkeypatch):
        inst = _fresh_mcp(monkeypatch, client_id=None, client_secret="csecret")
        assert inst._auth_server_provider is None
