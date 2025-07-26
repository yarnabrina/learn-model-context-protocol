"""Implement a basic MCP server with arithmetic operations."""

from .configurations import Configurations as MCPServerConfigurations
from .main import main as mcp_server_main

__all__ = ["MCPServerConfigurations", "mcp_server_main"]
