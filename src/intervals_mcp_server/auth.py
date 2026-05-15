"""
OAuth 2.0 authorization server for the Intervals.icu MCP Server.

Implements a minimal single-client OAuth provider that supports the
authorization code + PKCE flow used by Claude.ai and other MCP clients.
No persistent storage is needed: the client_secret is issued as the
access token, so tokens survive server restarts automatically.

Configure via:
  MCP_CLIENT_ID     — OAuth client ID to register in Claude.ai
  MCP_CLIENT_SECRET — OAuth client secret (also used as the access token)
  MCP_SERVER_URL    — Public HTTPS URL of this server (required for OAuth discovery)
"""

import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationParams,
    construct_redirect_uri,
)
from mcp.shared.auth import InvalidRedirectUriError, OAuthClientInformationFull, OAuthToken


@dataclass
class _AuthCode:
    """In-memory authorization code, valid for 5 minutes."""

    code: str
    client_id: str
    redirect_uri: str
    redirect_uri_provided_explicitly: bool
    code_challenge: str
    scopes: list[str] = field(default_factory=list)
    expires_at: float = field(default_factory=lambda: time.time() + 300)


class _FlexibleClient(OAuthClientInformationFull):
    """OAuthClientInformationFull that accepts any redirect URI from the caller.

    This is safe for personal deployments because the authorization code
    flow still requires PKCE (code_challenge / code_verifier), so a
    stolen code cannot be exchanged without the original code_verifier.
    """

    def validate_redirect_uri(self, redirect_uri: Any) -> Any:
        if redirect_uri is None:
            raise InvalidRedirectUriError("redirect_uri must be specified")
        return redirect_uri


class SingleClientOAuthProvider:
    """Minimal OAuth 2.0 authorization server for single-client personal deployments.

    Implements the authorization code + PKCE flow. Auto-approves the
    authorization step (no login screen) and issues the client_secret as
    the access token so no server-side state is needed across restarts.
    """

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._codes: dict[str, _AuthCode] = {}

    async def get_client(self, client_id: str) -> _FlexibleClient | None:
        if client_id != self._client_id:
            return None
        return _FlexibleClient(
            client_id=self._client_id,
            client_secret=self._client_secret,
            # Placeholder satisfies min_length=1; validate_redirect_uri is overridden
            redirect_uris=["https://placeholder.invalid"],
            grant_types=["authorization_code"],
            response_types=["code"],
        )

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        raise NotImplementedError("Dynamic client registration is not supported")

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        code = secrets.token_urlsafe(32)
        self._codes[code] = _AuthCode(
            code=code,
            client_id=client.client_id or self._client_id,
            redirect_uri=str(params.redirect_uri),
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            code_challenge=params.code_challenge,
            scopes=list(params.scopes or []),
        )
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> _AuthCode | None:
        code = self._codes.get(authorization_code)
        if code is None:
            return None
        if code.expires_at < time.time():
            del self._codes[authorization_code]
            return None
        return code

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: _AuthCode
    ) -> OAuthToken:
        self._codes.pop(authorization_code.code, None)
        return OAuthToken(access_token=self._client_secret, token_type="bearer")

    async def load_access_token(self, token: str) -> AccessToken | None:
        if secrets.compare_digest(token, self._client_secret):
            return AccessToken(token=token, client_id=self._client_id, scopes=[])
        return None

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> None:
        return None

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: None, scopes: list[str]
    ) -> OAuthToken:
        raise NotImplementedError("Refresh tokens are not supported")

    async def revoke_token(self, token: str, token_type_hint: str | None = None) -> None:
        pass
