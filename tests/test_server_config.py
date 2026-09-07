"""
Tests for server configuration — specifically that FASTMCP_HOST env var
is respected when starting the FastMCP server.
"""

import os
import sys
import pathlib
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.server_setup import start_server  # noqa: E402
from intervals_mcp_server.utils.types import TransportAliases  # noqa: E402


def test_fastmcp_host_default_is_localhost(monkeypatch):
    """When FASTMCP_HOST is not set, the server should bind to 127.0.0.1."""
    monkeypatch.delenv("FASTMCP_HOST", raising=False)
    mcp_instance = MagicMock()

    start_server(mcp_instance, TransportAliases.STREAMABLE_HTTP)

    mcp_instance.run.assert_called_once_with(
        transport="streamable-http", host="127.0.0.1", port=8000
    )


def test_fastmcp_host_reads_from_env(monkeypatch):
    """When FASTMCP_HOST=0.0.0.0 is set, the server should bind to 0.0.0.0."""
    monkeypatch.setenv("FASTMCP_HOST", "0.0.0.0")
    mcp_instance = MagicMock()

    start_server(mcp_instance, TransportAliases.STREAMABLE_HTTP)

    mcp_instance.run.assert_called_once_with(transport="streamable-http", host="0.0.0.0", port=8000)
