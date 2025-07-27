"""Implement client-side logic for MCP server management."""

import collections.abc
import enum
import json

import pydantic
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.metadata_utils import get_display_name
from mcp.types import TextContent, ToolAnnotations
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
    ChatCompletionToolParam,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function
from openai.types.shared_params import FunctionDefinition

from .configurations import Configurations
from .console import internal_info
from .llm import OpenAIClient


class MCPTool(pydantic.BaseModel):
    """Define a tool available on an MCP server."""

    name: str
    display_name: str
    title: str | None = None
    description: str | None = None
    input_schema: dict
    output_schema: dict | None = None
    annotations: ToolAnnotations | None = None


class Status(enum.StrEnum):
    """Define the status of an MCP server addition or removal operation."""

    SUCCESS = "success"
    FAILURE = "failure"


class OpenAIFunctionDefinition(pydantic.BaseModel):
    """Define an OpenAI API compatible function definition for MCP tools."""

    name: str
    description: str | None = None
    parameters: dict | None = None


class MCPClient:
    """Define a client for managing MCP servers and their tools.

    Parameters
    ----------
    settings : Configurations
        language model configurations containing API keys and customisations

    Attributes
    ----------
    mcp_servers : dict[str, str]
        mapping of MCP server names to their URLs
    mcp_server_tools : dict[str, list[MCPTool]]
        mapping of MCP server names to their available tools
    openai_client : OpenAIClient
        client for interacting with OpenAI API for tool calls
    """

    def __init__(self: "MCPClient", settings: Configurations) -> None:
        self.settings = settings

        self.mcp_servers: dict[str, str] = {}
        self.mcp_server_tools: dict[str, list[MCPTool]] = {}

        self.openai_client = OpenAIClient(self.settings)

    async def add_mcp_server(self: "MCPClient", server_name: str, server_url: str) -> list[str]:
        """Add a new MCP server and retrieve its available tools.

        Parameters
        ----------
        server_name : str
            name of the MCP server to add
        server_url : str
            URL of the MCP server to add

        Returns
        -------
        list[str]
            list of tool names available on the added MCP server
        """
        self.mcp_servers[server_name] = server_url

        try:
            async with streamablehttp_client(server_url) as (  # noqa: SIM117
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    server_tools = await session.list_tools()
        except ExceptionGroup as errors_group:
            internal_info(f"Failed to add MCP server {server_name} at {server_url}.\n")

            for error in errors_group.exceptions:
                internal_info(f"Sub-exception: {error}.\n")

            _ = self.mcp_servers.pop(server_name)

            return []
        except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
            internal_info(f"Failed to add MCP server {server_name} at {server_url}: {error}.\n")

            _ = self.mcp_servers.pop(server_name)

            return []

        processed_server_tools = [
            MCPTool(
                name=tool.name,
                display_name=get_display_name(tool),
                title=tool.title,
                description=tool.description,
                input_schema=tool.inputSchema,
                output_schema=tool.outputSchema,
                annotations=tool.annotations,
            )
            for tool in server_tools.tools
        ]
        self.mcp_server_tools[server_name] = processed_server_tools

        return [tool.display_name for tool in processed_server_tools]

    def list_mcp_servers(self: "MCPClient") -> dict[str, str]:
        """List all added MCP servers.

        Returns
        -------
        dict[str, str]
            mapping of MCP server names to their URLs
        """
        return self.mcp_servers

    def remove_mcp_server(self: "MCPClient", server_name: str) -> Status:
        """Remove an MCP server by its name.

        Parameters
        ----------
        server_name : str
            name of the MCP server to remove

        Returns
        -------
        Status
            status of the removal operation
        """
        try:
            _ = self.mcp_servers.pop(server_name)
            _ = self.mcp_server_tools.pop(server_name)
        except KeyError as error:
            internal_info(f"Failed to remove MCP server {server_name}: {error}.\n")

            return Status.FAILURE

        return Status.SUCCESS

    def list_mcp_server_tools(self: "MCPClient", server_name: str) -> list[str]:
        """List all tools available on a specific MCP server.

        Parameters
        ----------
        server_name : str
            name of the MCP server to list tools for

        Returns
        -------
        list[str]
            list of tool names available on the specified MCP server
        """
        try:
            server_tools = self.mcp_server_tools[server_name]
        except KeyError as error:
            internal_info(f"Failed to remove MCP server {server_name}: {error}.\n")

            return []

        return [tool.display_name for tool in server_tools]

    def describe_mcp_server_tool(
        self: "MCPClient", server_name: str, tool_name: str
    ) -> MCPTool | None:
        """Describe a specific tool available on an MCP server.

        Parameters
        ----------
        server_name : str
            name of the MCP server to describe the tool for
        tool_name : str
            name of the tool to describe

        Returns
        -------
        MCPTool | None
            tool details if found, None otherwise
        """
        try:
            server_tools = self.mcp_server_tools[server_name]
        except KeyError as error:
            internal_info(f"MCP server {server_name} does not exist: {error}.\n")

            return

        for tool in server_tools:
            if tool.name == tool_name:
                return tool

        internal_info(f"Tool {tool_name} does not exist in MCP server {server_name}.\n")

    async def get_all_openai_functions(self: "MCPClient") -> list[ChatCompletionToolParam]:
        """Get all MCP tools as OpenAI API compatible function definitions.

        Returns
        -------
        list[ChatCompletionToolParam]
            list of OpenAI API compatible function definitions for all MCP tools
        """
        return [
            ChatCompletionToolParam(
                function=FunctionDefinition(
                    name=f"mcp-{server_name}-{tool.name}",
                    description=tool.description or "",
                    parameters=tool.input_schema,
                ),
                type="function",
            )
            for server_name, server_tools in self.mcp_server_tools.items()
            for tool in server_tools
        ]

    async def execute_tool_call(  # noqa: PLR0911
        self: "MCPClient", tool_name: str, arguments: dict
    ) -> str:
        """Execute a tool call on an MCP server.

        Parameters
        ----------
        tool_name : str
            name of the tool to call, formatted as "mcp-{server_name}-{tool_name}"
        arguments : dict
            arguments to pass to the tool call

        Returns
        -------
        str
            JSON string containing the result of the tool call or an error message
        """
        if not tool_name.startswith("mcp-"):
            return json.dumps({"error": f"Unknown MCP tool {tool_name}."})

        _, server_name, actual_tool_name = tool_name.split(sep="-", maxsplit=2)

        if server_name not in self.mcp_servers:
            return json.dumps({"error": f"Unknown MCP connection {server_name}."})

        server_url = self.mcp_servers[server_name]

        internal_info(
            f"Calling tool {actual_tool_name} "
            f"from MCP server {server_name} ({server_url}) "
            f"with following parameters: {arguments}.\n"
        )

        try:
            async with streamablehttp_client(server_url) as (  # noqa: SIM117
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    tool_result = await session.call_tool(actual_tool_name, arguments=arguments)
        except ExceptionGroup as errors_group:
            internal_info(f"Failed tool call to {actual_tool_name} of MCP server {server_name}.\n")

            for error in errors_group.exceptions:
                internal_info(f"Sub-exception: {error}.\n")

            return json.dumps({"error": f"Failed tool call to {actual_tool_name}."})
        except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
            internal_info(
                f"Failed tool call to {actual_tool_name} of MCP server {server_name}: {error}.\n"
            )

            return json.dumps({"error": f"Failed tool call to {actual_tool_name}: {error}."})

        internal_info(
            f"Received response from tool {actual_tool_name} "
            f"of MCP server {server_name} ({server_url}) "
            f"as following: {tool_result}.\n"
        )

        if tool_result.isError:
            error_message = "".join(
                content.text for content in tool_result.content if isinstance(content, TextContent)
            )

            return json.dumps(
                {
                    "error": (
                        f"Failed tool call to {tool_name=} with {arguments=}: {error_message}."
                    )
                }
            )

        if (structured_result := tool_result.structuredContent) is not None:
            return json.dumps(structured_result)

        return json.dumps(tool_result.content)


class OpenAIOrchestrator:
    """Define an orchestrator for handling OpenAI API calls with MCP tools.

    Parameters
    ----------
    mcp_client : MCPClient
        client for managing MCP servers and their tools
    settings : Configurations
        language model configurations containing API keys and customisations

    Attributes
    ----------
    openai_client : OpenAIClient
        client for interacting with OpenAI API for tool calls
    conversation_history : list[ChatCompletionMessageParam]
        history of conversation messages for the OpenAI API
    """

    def __init__(
        self: "OpenAIOrchestrator",
        mcp_client: MCPClient,
        settings: Configurations,
        system_prompt: str | None = None,
    ) -> None:
        self.mcp_client = mcp_client
        self.settings = settings
        self.system_prompt = system_prompt

        self.openai_client = OpenAIClient(self.settings)
        self.conversation_history: list[ChatCompletionMessageParam] = []

    async def call_openai(
        self: "OpenAIOrchestrator",
    ) -> collections.abc.AsyncGenerator[tuple[str | None, str | None, list[dict]]]:
        """Call OpenAI API with the current conversation history and available tools.

        Yields
        ------
        str | None
            finish reason from the OpenAI API response
        str | None
            token content from the OpenAI API response
        list[dict]
            tool calls from the OpenAI API response
        """
        available_openai_tools = await self.mcp_client.get_all_openai_functions()

        chat_completion = self.openai_client.get_streaming_openai_response(
            self.conversation_history,
            system_prompt=self.system_prompt,
            tools=available_openai_tools,
        )

        tool_calls: dict[int, ChatCompletionMessageToolCallParam] = {}
        async for chunk in chat_completion:
            if not chunk.choices:
                continue

            chunk_response = chunk.choices[0]

            for tool_call in chunk_response.delta.tool_calls or []:
                index = tool_call.index

                if index not in tool_calls:
                    tool_calls[index] = ChatCompletionMessageToolCallParam(
                        id=tool_call.id,
                        function=Function(arguments="", name=tool_call.function.name),
                        type=tool_call.type,
                    )

                if (arguments := tool_call.function.arguments) is not None:
                    tool_calls[index]["function"]["arguments"] += arguments

            finish_reason = chunk_response.finish_reason

            if (token := chunk_response.delta.content) is not None:
                yield finish_reason, token, [tool_call for _, tool_call in tool_calls.items()]

            yield finish_reason, None, [tool_call for _, tool_call in tool_calls.items()]

    async def process_user_message(  # noqa: C901, PLR0912
        self: "OpenAIOrchestrator", user_message: str
    ) -> collections.abc.AsyncGenerator[tuple[str, bool]]:
        """Process a user message and generate a response using OpenAI API.

        Parameters
        ----------
        user_message : str
            new message from the user to process

        Yields
        ------
        str
            token content from the OpenAI API response
        bool
            whether the token is the initial token of the response
        """
        self.conversation_history.append({"role": "user", "content": user_message})

        initial_token = True
        assistant_message = ""
        async for (
            finish_reason_delta,
            assistant_message_token,
            assistant_tool_calls_delta,
        ) in self.call_openai():
            if assistant_message_token:
                assistant_message += assistant_message_token

                if initial_token:
                    initial_token = False

                    yield assistant_message_token, True
                else:
                    yield assistant_message_token, False

            if finish_reason_delta:
                finish_reason = finish_reason_delta
                assistant_tool_calls = assistant_tool_calls_delta

                yield "\n", False

                break
        else:
            yield "\n", False

        while finish_reason == "tool_calls":
            self.conversation_history.append(
                ChatCompletionAssistantMessageParam(
                    role="assistant", content=assistant_message, tool_calls=assistant_tool_calls
                )
            )

            internal_info(f"Identified tool calls: {assistant_tool_calls}.\n")

            for tool_call in assistant_tool_calls:
                try:
                    tool_arguments = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError as error:
                    self.conversation_history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": f"Error: {error}",
                        }
                    )
                else:
                    tool_execution_result = await self.mcp_client.execute_tool_call(
                        tool_call["function"]["name"], tool_arguments
                    )

                    self.conversation_history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_execution_result,
                        }
                    )

            initial_token = True
            assistant_message = ""
            async for (
                finish_reason_delta,
                assistant_message_token,
                assistant_tool_calls_delta,
            ) in self.call_openai():
                if assistant_message_token:
                    assistant_message += assistant_message_token

                    if initial_token:
                        initial_token = False

                        yield assistant_message_token, True
                    else:
                        yield assistant_message_token, False

                if finish_reason_delta:
                    finish_reason = finish_reason_delta
                    assistant_tool_calls = assistant_tool_calls_delta

                    yield "\n", False

                    break
            else:
                yield "\n", False

        self.conversation_history.append({"role": "assistant", "content": assistant_message})
