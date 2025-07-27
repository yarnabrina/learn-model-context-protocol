"""Initialise a basic MCP server with arithmetic operations."""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .arithmetic_operations import (
    add_numbers,
    divide_numbers,
    get_negative,
    get_reciprocal,
    multiply_numbers,
    subtract_numbers,
)
from .configurations import Configurations
from .simplification import evaluate_arithmetic_expression, parse_arithmetic_expression


def main() -> None:
    """Define entry point for the MCP server."""
    settings = Configurations()

    mcp_server = FastMCP(
        name="Basic MCP Server for Demonstration",
        debug=settings.debug,
        log_level=settings.log_level,
        host=settings.host,
        port=settings.port,
        streamable_http_path=settings.streamable_http_path,
        json_response=settings.json_response,
        stateless_http=settings.stateless_http,
    )

    mcp_server.add_tool(
        add_numbers,
        title="Add Numbers",
        description="Perform addition of two real numbers",
        annotations=ToolAnnotations(title="Addition", readOnlyHint=True, openWorldHint=False),
        structured_output=True,
    )
    mcp_server.add_tool(
        get_negative,
        title="Get Negative",
        description="Get additive inverse of a real number",
        annotations=ToolAnnotations(
            title="Additive Inverse", readOnlyHint=True, openWorldHint=False
        ),
        structured_output=True,
    )
    mcp_server.add_tool(
        subtract_numbers,
        title="Subtract Numbers",
        description="Perform subtraction of two real numbers",
        annotations=ToolAnnotations(title="Subtraction", readOnlyHint=True, openWorldHint=False),
        structured_output=True,
    )
    mcp_server.add_tool(
        multiply_numbers,
        title="Multiply Numbers",
        description="Perform multiplication of two real numbers",
        annotations=ToolAnnotations(
            title="Multiplication", readOnlyHint=True, openWorldHint=False
        ),
        structured_output=True,
    )
    mcp_server.add_tool(
        get_reciprocal,
        title="Get Reciprocal",
        description="Get multiplicative inverse of a real number",
        annotations=ToolAnnotations(
            title="Multiplicative Inverse", readOnlyHint=True, openWorldHint=False
        ),
        structured_output=True,
    )
    mcp_server.add_tool(
        divide_numbers,
        title="Divide Numbers",
        description="Perform division of two real numbers",
        annotations=ToolAnnotations(title="Division", readOnlyHint=True, openWorldHint=False),
        structured_output=True,
    )
    mcp_server.add_tool(
        parse_arithmetic_expression,
        title="Parse Arithmetic Expression",
        description="Parse a text into a valid arithmetic expression",
        annotations=ToolAnnotations(
            title="Arithmetic Expression Parser", readOnlyHint=True, openWorldHint=True
        ),
        structured_output=False,
    )
    mcp_server.add_tool(
        evaluate_arithmetic_expression,
        title="Evaluate Arithmetic Expression",
        description="Evaluate a valid postfix arithmetic expression",
        annotations=ToolAnnotations(
            title="Arithmetic Expression Evaluator", readOnlyHint=True, openWorldHint=False
        ),
        structured_output=False,
    )

    mcp_server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
