"""Initialise a basic MCP server with arithmetic operations."""

import asyncio
import logging
import typing

from fastmcp import FastMCP
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import Tool, ToolResult
from fastmcp.utilities.logging import get_logger
from mcp.types import CallToolRequestParams, ToolAnnotations

from ..logging_bootstrap import (
    LoggingBootstrapSettings,
    LoggingComponent,
    initiate_logging,
    resolve_fastmcp_log_level,
)
from .arithmetic_operations import (
    add_numbers,
    divide_numbers,
    get_negative,
    get_reciprocal,
    multiply_numbers,
    subtract_numbers,
)
from .configurations import Configurations
from .exponentiation import exponentiate
from .simplification import evaluate_arithmetic_expression, parse_arithmetic_expression

LOGGER = logging.getLogger(__name__)

CLIENT_LOGGER = get_logger("fastmcp.server.context.to_client")

CLIENT_LOGGER.setLevel(logging.DEBUG)


class ToolLoggingMiddleware(Middleware):
    """Log tool calls through the project's structured logger."""

    async def on_call_tool(
        self: typing.Self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        """Log a tool call before and after dispatch.

        Parameters
        ----------
        context : MiddlewareContext[CallToolRequestParams]
            tool name and arguments for the incoming request
        call_next : CallNext[CallToolRequestParams, ToolResult]
            next middleware or tool handler in the dispatch chain

        Returns
        -------
        ToolResult
            tool result, including an error result returned by the tool

        Raises
        ------
        Exception
            re-raises an exception from downstream middleware or the tool
        """
        tool_name = context.message.name
        arguments = context.message.arguments

        LOGGER.info(
            f"Received tool call for {tool_name=} with {arguments=}.",
            extra={
                "event.group": "tool",
                "event.type": "local_call",
                "event.action": "execute",
                "event.status": "started",
                "tool.name": tool_name,
            },
        )

        try:
            result = await call_next(context)
        except Exception:
            LOGGER.exception(
                f"Tool call for {tool_name=} failed.",
                exc_info=True,
                extra={
                    "event.group": "tool",
                    "event.type": "local_call",
                    "event.action": "execute",
                    "event.status": "failed",
                    "tool.name": tool_name,
                },
            )

            raise

        log_method = LOGGER.error if result.is_error else LOGGER.info
        log_method(
            f"Tool call for {tool_name=} {'failed' if result.is_error else 'succeeded'} "
            f"with {result=}.",
            extra={
                "event.group": "tool",
                "event.type": "local_call",
                "event.action": "execute",
                "event.status": "failed" if result.is_error else "succeeded",
                "tool.name": tool_name,
            },
        )

        return result


class ArithmeticMCPServer:
    """Define the MCP server for handling arithmetic operations.

    Parameters
    ----------
    settings : Configurations
        server configurations containing host, port, and other settings

    Attributes
    ----------
    mcp_server : FastMCP
        MCP server instance configured based on the provided settings
    """

    def __init__(self: typing.Self, settings: Configurations) -> None:
        self.settings = settings

        self.mcp_server: FastMCP = self.initiate_mcp_server()

        self.configure_mcp_server_tools()

    def initiate_mcp_server(self: typing.Self) -> FastMCP:
        """Initialize the MCP server with the provided settings.

        Returns
        -------
        FastMCP
            configured MCP server instance
        """
        return FastMCP(
            name="Basic MCP Server for Demonstration",
            instructions=(
                "MCP server that can perform basic arithmetic operations"
                " and parse/evaluate arithmetic expressions."
            ),
            version="0.3.0",
            website_url=(
                "https://registry.modelcontextprotocol.io/servers/"
                "io.github.yarnabrina/mcp-learning"
            ),
            middleware=[ToolLoggingMiddleware()],
            on_duplicate="error",
            mask_error_details=False,
            strict_input_validation=True,
        )

    def configure_mcp_server_tools(self: typing.Self) -> None:
        """Configure and add arithmetic operation tools to the MCP server."""
        self.mcp_server.add_tool(
            Tool.from_function(
                add_numbers,
                name="addition",
                title="Add Numbers",
                description="Perform addition of two real numbers",
                annotations=ToolAnnotations(
                    title="Addition", read_only_hint=True, open_world_hint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                get_negative,
                name="negation",
                title="Get Negative",
                description="Get additive inverse of a real number",
                annotations=ToolAnnotations(
                    title="Additive Inverse", read_only_hint=True, open_world_hint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                subtract_numbers,
                name="subtraction",
                title="Subtract Numbers",
                description="Perform subtraction of two real numbers",
                annotations=ToolAnnotations(
                    title="Subtraction", read_only_hint=True, open_world_hint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                multiply_numbers,
                name="multiplication",
                title="Multiply Numbers",
                description="Perform multiplication of two real numbers",
                annotations=ToolAnnotations(
                    title="Multiplication", read_only_hint=True, open_world_hint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                get_reciprocal,
                name="reciprocal",
                title="Get Reciprocal",
                description="Get multiplicative inverse of a real number",
                annotations=ToolAnnotations(
                    title="Multiplicative Inverse", read_only_hint=True, open_world_hint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                divide_numbers,
                name="division",
                title="Divide Numbers",
                description="Perform division of two real numbers",
                annotations=ToolAnnotations(
                    title="Division", read_only_hint=True, open_world_hint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                parse_arithmetic_expression,
                name="parse_expression",
                title="Parse Arithmetic Expression",
                description="Parse a text into a valid arithmetic expression",
                annotations=ToolAnnotations(
                    title="Arithmetic Expression Parser", read_only_hint=True, open_world_hint=True
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                evaluate_arithmetic_expression,
                name="evaluate_expression",
                title="Evaluate Arithmetic Expression",
                description="Evaluate a valid postfix arithmetic expression",
                annotations=ToolAnnotations(
                    title="Arithmetic Expression Evaluator",
                    read_only_hint=True,
                    open_world_hint=False,
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                exponentiate,
                name="exponentiation",
                title="Power",
                description="Raise a base to an exponent",
                annotations=ToolAnnotations(
                    title="Exponentiation", read_only_hint=True, open_world_hint=False
                ),
            )
        )


def main() -> None:
    """Define entry point for the MCP server."""
    settings = Configurations()

    logging_settings = LoggingBootstrapSettings(
        component=LoggingComponent.MCP_SERVER,
        debug=settings.debug,
        log_level=settings.log_level,
        runtime_environment=settings.runtime_environment,
        log_file=settings.log_file,
    )

    initiate_logging(logging_settings)

    LOGGER.info(
        "MCP server startup began.",
        extra={
            "event.group": "runtime",
            "event.type": "lifecycle",
            "event.action": "start",
            "event.status": "started",
        },
    )

    try:
        arithmetic_mcp_server = ArithmeticMCPServer(settings)
    except Exception:
        LOGGER.exception(
            "MCP server startup failed.",
            exc_info=True,
            extra={
                "event.group": "runtime",
                "event.type": "lifecycle",
                "event.action": "start",
                "event.status": "failed",
            },
        )

        raise

    LOGGER.info(
        "MCP server configuration completed.",
        extra={
            "event.group": "runtime",
            "event.type": "configuration",
            "event.action": "configure",
            "event.status": "succeeded",
        },
    )

    effective_log_level = resolve_fastmcp_log_level(logging_settings)

    asyncio.run(
        arithmetic_mcp_server.mcp_server.run_http_async(
            show_banner=False,
            transport="streamable-http",
            host=settings.host,
            port=settings.port,
            log_level=effective_log_level,
            path=settings.streamable_http_path,
            json_response=settings.json_response,
            stateless_http=settings.stateless_http,
        )
    )


if __name__ == "__main__":
    main()
