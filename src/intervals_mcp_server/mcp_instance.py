"""
Shared MCP instance module.

This module provides a shared FastMCP instance that can be imported by both
the server module and tool modules without creating cyclic imports.
"""

import logging
import os

from pydantic import AnyHttpUrl

from mcp.server.fastmcp import FastMCP

from intervals_mcp_server.api.client import setup_api_client

logger = logging.getLogger("intervals_icu_mcp_server")

_mcp_client_id = os.getenv("MCP_CLIENT_ID", "")
_mcp_client_secret = os.getenv("MCP_CLIENT_SECRET", "")
_mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

_auth_server_provider = None
_auth_settings = None

if _mcp_client_id and _mcp_client_secret:
    from intervals_mcp_server.auth import SingleClientOAuthProvider
    from mcp.server.auth.settings import AuthSettings

    _auth_server_provider = SingleClientOAuthProvider(_mcp_client_id, _mcp_client_secret)
    # issuer_url must be the public HTTPS URL of this server so that
    # Claude.ai can discover the OAuth endpoints via /.well-known/oauth-authorization-server
    _auth_settings = AuthSettings(
        issuer_url=AnyHttpUrl(_mcp_server_url),
        resource_server_url=None,
    )
    logger.info("OAuth authentication enabled for HTTP transport.")
else:
    logger.debug("MCP_CLIENT_ID/MCP_CLIENT_SECRET not set; HTTP endpoint is unauthenticated.")

mcp: FastMCP = FastMCP(
    "intervals-icu",
    lifespan=setup_api_client,
    host=os.getenv("FASTMCP_HOST", "127.0.0.1"),
    auth_server_provider=_auth_server_provider,
    auth=_auth_settings,
)
