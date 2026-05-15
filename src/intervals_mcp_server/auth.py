"""
Bearer token authentication for the Intervals.icu MCP Server.

Implements a TokenVerifier that validates a static API key supplied via the
MCP_API_KEY environment variable.  This is only active for HTTP transports;
stdio transport is unaffected because FastMCP does not apply auth middleware
to the stdio code path.
"""

import secrets

from mcp.server.auth.provider import AccessToken


class StaticTokenVerifier:
    """Validates incoming bearer tokens against a single pre-shared secret.

    Comparison uses secrets.compare_digest to avoid timing-based attacks.
    """

    def __init__(self, expected_token: str) -> None:
        self._expected = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if secrets.compare_digest(token, self._expected):
            return AccessToken(token=token, client_id="mcp-client", scopes=[])
        return None
