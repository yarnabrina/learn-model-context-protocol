"""Initialise a basic MCP server with arithmetic operations."""

import asyncio
import collections.abc
import functools
import logging
import typing

from fastmcp import FastMCP
from fastmcp.tools import Tool
from mcp.types import ToolAnnotations

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


def create_logged_tool(
    tool_callable: collections.abc.Callable, tool_name: str
) -> collections.abc.Callable:
    """Wrap a callable tool to log its input and output.

    Parameters
    ----------
    tool_callable : collections.abc.Callable
        the original tool function to be wrapped
    tool_name : str
        name of the tool for logging purposes

    Returns
    -------
    collections.abc.Callable
        wrapped tool function with logging functionality
    """

    @functools.wraps(tool_callable)
    async def logged_tool(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:  # noqa: ANN401
        """Log the input arguments and output result of the tool function.

        Parameters
        ----------
        *args : tuple
            positional arguments passed to the tool function
        **kwargs : dict
            keyword arguments passed to the tool function

        Returns
        -------
        typing.Any
            result returned by the original tool function
        """
        LOGGER.info(
            f"Received tool call for {tool_name=} with {args=} and {kwargs=}.",
            extra={
                "event.group": "tool",
                "event.type": "local_call",
                "event.action": "execute",
                "event.status": "started",
                "tool.name": tool_name,
            },
        )

        try:
            if asyncio.iscoroutinefunction(tool_callable):
                result = await tool_callable(*args, **kwargs)
            else:
                result = tool_callable(*args, **kwargs)
        except ExceptionGroup:
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

        LOGGER.info(
            f"Tool call for {tool_name=} succeeded with {result=}.",
            extra={
                "event.group": "tool",
                "event.type": "local_call",
                "event.action": "execute",
                "event.status": "succeeded",
                "tool.name": tool_name,
            },
        )

        return result

    return logged_tool


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
            version="0.2.0",
            website_url="https://registry.modelcontextprotocol.io/servers/io.github.yarnabrina/mcp-learning",
            on_duplicate="error",
            mask_error_details=False,
            strict_input_validation=True,
        )

    def configure_mcp_server_tools(self: typing.Self) -> None:
        """Configure and add arithmetic operation tools to the MCP server."""
        self.mcp_server.add_tool(
            Tool.from_function(
                create_logged_tool(add_numbers, "addition"),
                name="addition",
                title="Add Numbers",
                description="Perform addition of two real numbers",
                annotations=ToolAnnotations(
                    title="Addition", readOnlyHint=True, openWorldHint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                create_logged_tool(get_negative, "negation"),
                name="negation",
                title="Get Negative",
                description="Get additive inverse of a real number",
                annotations=ToolAnnotations(
                    title="Additive Inverse", readOnlyHint=True, openWorldHint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                create_logged_tool(subtract_numbers, "subtraction"),
                name="subtraction",
                title="Subtract Numbers",
                description="Perform subtraction of two real numbers",
                annotations=ToolAnnotations(
                    title="Subtraction", readOnlyHint=True, openWorldHint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                create_logged_tool(multiply_numbers, "multiplication"),
                name="multiplication",
                title="Multiply Numbers",
                description="Perform multiplication of two real numbers",
                annotations=ToolAnnotations(
                    title="Multiplication", readOnlyHint=True, openWorldHint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                create_logged_tool(get_reciprocal, "reciprocal"),
                name="reciprocal",
                title="Get Reciprocal",
                description="Get multiplicative inverse of a real number",
                annotations=ToolAnnotations(
                    title="Multiplicative Inverse", readOnlyHint=True, openWorldHint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                create_logged_tool(divide_numbers, "division"),
                name="division",
                title="Divide Numbers",
                description="Perform division of two real numbers",
                annotations=ToolAnnotations(
                    title="Division", readOnlyHint=True, openWorldHint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                create_logged_tool(parse_arithmetic_expression, "parse_expression"),
                name="parse_expression",
                title="Parse Arithmetic Expression",
                description="Parse a text into a valid arithmetic expression",
                annotations=ToolAnnotations(
                    title="Arithmetic Expression Parser", readOnlyHint=True, openWorldHint=True
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                create_logged_tool(evaluate_arithmetic_expression, "evaluate_expression"),
                name="evaluate_expression",
                title="Evaluate Arithmetic Expression",
                description="Evaluate a valid postfix arithmetic expression",
                annotations=ToolAnnotations(
                    title="Arithmetic Expression Evaluator", readOnlyHint=True, openWorldHint=False
                ),
            )
        )
        self.mcp_server.add_tool(
            Tool.from_function(
                create_logged_tool(exponentiate, "exponentiation"),
                name="exponentiation",
                title="Power",
                description="Raise a base to an exponent",
                annotations=ToolAnnotations(
                    title="Exponentiation", readOnlyHint=True, openWorldHint=False
                ),
            )
        )


def main() -> None:
    """Define entry point for the MCP server."""
    settings = Configurations()

    initiate_logging(
        LoggingBootstrapSettings(
            component=LoggingComponent.MCP_SERVER,
            debug=settings.debug,
            log_level=settings.log_level,
            runtime_environment=settings.runtime_environment,
            log_file=settings.log_file,
        )
    )

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
        "MCP server startup completed.",
        extra={
            "event.group": "runtime",
            "event.type": "lifecycle",
            "event.action": "start",
            "event.status": "succeeded",
        },
    )

    effective_log_level = resolve_fastmcp_log_level(
        LoggingBootstrapSettings(
            component=LoggingComponent.MCP_SERVER,
            runtime_environment=settings.runtime_environment,
            debug=settings.debug,
            log_level=settings.log_level,
            log_file=settings.log_file,
        )
    )

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

    arithmetic_mcp_server.mcp_server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
