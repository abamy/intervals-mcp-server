"""
Tests for bearer token authentication.

Covers StaticTokenVerifier and the conditional wiring of auth into the
FastMCP instance via MCP_API_KEY.
"""

import os
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")


def _fresh_mcp(monkeypatch, mcp_api_key=None):
    """Reimport mcp_instance with a clean module cache and given MCP_API_KEY."""
    if mcp_api_key is not None:
        monkeypatch.setenv("MCP_API_KEY", mcp_api_key)
    else:
        monkeypatch.delenv("MCP_API_KEY", raising=False)

    for key in list(sys.modules.keys()):
        if "intervals_mcp_server" in key:
            del sys.modules[key]

    import intervals_mcp_server.mcp_instance as inst  # pylint: disable=import-outside-toplevel

    return inst


class TestStaticTokenVerifier:
    @pytest.mark.asyncio
    async def test_accepts_correct_token(self):
        from intervals_mcp_server.auth import StaticTokenVerifier  # pylint: disable=import-outside-toplevel

        verifier = StaticTokenVerifier("secret123")
        result = await verifier.verify_token("secret123")
        assert result is not None
        assert result.client_id == "mcp-client"

    @pytest.mark.asyncio
    async def test_rejects_wrong_token(self):
        from intervals_mcp_server.auth import StaticTokenVerifier  # pylint: disable=import-outside-toplevel

        verifier = StaticTokenVerifier("secret123")
        result = await verifier.verify_token("wrong")
        assert result is None

    @pytest.mark.asyncio
    async def test_rejects_empty_token(self):
        from intervals_mcp_server.auth import StaticTokenVerifier  # pylint: disable=import-outside-toplevel

        verifier = StaticTokenVerifier("secret123")
        result = await verifier.verify_token("")
        assert result is None


class TestMcpInstanceAuth:
    def test_no_auth_when_mcp_api_key_unset(self, monkeypatch):
        inst = _fresh_mcp(monkeypatch, mcp_api_key=None)
        assert inst._token_verifier is None
        assert inst._auth_settings is None

    def test_auth_enabled_when_mcp_api_key_set(self, monkeypatch):
        inst = _fresh_mcp(monkeypatch, mcp_api_key="supersecret")
        assert inst._token_verifier is not None
        assert inst._auth_settings is not None

    def test_auth_disabled_for_empty_mcp_api_key(self, monkeypatch):
        inst = _fresh_mcp(monkeypatch, mcp_api_key="")
        assert inst._token_verifier is None
        assert inst._auth_settings is None

    @pytest.mark.asyncio
    async def test_token_verifier_validates_correct_token(self, monkeypatch):
        inst = _fresh_mcp(monkeypatch, mcp_api_key="mykey")
        result = await inst._token_verifier.verify_token("mykey")
        assert result is not None

    @pytest.mark.asyncio
    async def test_token_verifier_rejects_wrong_token(self, monkeypatch):
        inst = _fresh_mcp(monkeypatch, mcp_api_key="mykey")
        result = await inst._token_verifier.verify_token("notmykey")
        assert result is None
