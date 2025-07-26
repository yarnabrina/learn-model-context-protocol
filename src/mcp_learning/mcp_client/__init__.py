"""Implement a basic MCP client."""

from .configurations import Configurations as MCPClientConfigurations
from .main import main as mcp_client_main

__all__ = ["MCPClientConfigurations", "mcp_client_main"]
