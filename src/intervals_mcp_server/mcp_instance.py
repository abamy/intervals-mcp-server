"""
Shared MCP instance module.

This module provides a shared FastMCP instance that can be imported by both
the server module and tool modules without creating cyclic imports.
"""

import logging
import os

from mcp.server.fastmcp import FastMCP

from intervals_mcp_server.api.client import setup_api_client

logger = logging.getLogger("intervals_icu_mcp_server")

_mcp_api_key = os.getenv("MCP_API_KEY", "")

_token_verifier = None
_auth_settings = None

if _mcp_api_key:
    from intervals_mcp_server.auth import StaticTokenVerifier
    from mcp.server.auth.settings import AuthSettings

    _token_verifier = StaticTokenVerifier(_mcp_api_key)
    # issuer_url is required by AuthSettings but is unused when no OAuth
    # server provider is configured (resource_server_url=None, no auth routes).
    _auth_settings = AuthSettings(
        issuer_url=os.getenv("MCP_SERVER_URL", "http://localhost:8000"),
        resource_server_url=None,
    )
    logger.info("Bearer token authentication enabled for HTTP transport.")
else:
    logger.debug("MCP_API_KEY not set; HTTP endpoint is unauthenticated.")

mcp: FastMCP = FastMCP(
    "intervals-icu",
    lifespan=setup_api_client,
    host=os.getenv("FASTMCP_HOST", "127.0.0.1"),
    token_verifier=_token_verifier,
    auth=_auth_settings,
)
