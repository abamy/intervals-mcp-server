"""
Shared MCP instance module.

This module provides a shared FastMCP instance that can be imported by both
the server module and tool modules without creating cyclic imports.
"""

import logging
import os

from fastmcp import FastMCP

from intervals_mcp_server.api.client import setup_api_client

logger = logging.getLogger("intervals_icu_mcp_server")

_mcp_client_id = os.getenv("MCP_CLIENT_ID", "")
_mcp_client_secret = os.getenv("MCP_CLIENT_SECRET", "")
_mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

_auth_server_provider = None

if _mcp_client_id and _mcp_client_secret:
    from intervals_mcp_server.auth import SingleClientOAuthProvider

    # This server is both the authorization server and the resource server, so
    # base_url/issuer_url/resource_base_url all point at the same public HTTPS
    # URL: base_url/issuer_url publish /.well-known/oauth-authorization-server
    # (AS metadata) and resource_base_url publishes
    # /.well-known/oauth-protected-resource (RFC 9728), which Claude.ai's
    # connector flow requires to authorize.
    _auth_server_provider = SingleClientOAuthProvider(
        _mcp_client_id,
        _mcp_client_secret,
        base_url=_mcp_server_url,
    )
    logger.info("OAuth authentication enabled for HTTP transport.")
else:
    logger.debug("MCP_CLIENT_ID/MCP_CLIENT_SECRET not set; HTTP endpoint is unauthenticated.")

mcp: FastMCP = FastMCP(
    "intervals-icu",
    lifespan=setup_api_client,
    auth=_auth_server_provider,
)
