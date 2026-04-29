"""Implement client-side logic for MCP server management."""

import dataclasses
import enum
import functools
import json
import logging
import typing

import pydantic
from fastmcp import Client
from fastmcp.client import StreamableHttpTransport
from fastmcp.client.elicitation import ElicitResult
from mcp.shared.context import RequestContext
from mcp.shared.metadata_utils import get_display_name
from mcp.types import (
    INTERNAL_ERROR,
    CreateMessageRequestParams,
    CreateMessageResult,
    ElicitRequestParams,
    ErrorData,
    LoggingMessageNotificationParams,
    SamplingCapability,
    SamplingToolsCapability,
    TextContent,
    ToolAnnotations,
)
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionDeveloperMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params import FunctionDefinition

from .llm import OpenAIClient
from .utils import (
    Configurations,
    MonitoringClient,
    bot_response,
    trace_tool_input,
    trace_tool_output,
    user_prompt,
)

LOGGER = logging.getLogger(__name__)


ELICITATION_REQUEST_PROMPT = """You are an elicitation assistant.

- Your task is to help the user provide the required information for a tool call.
- The user has provided inputs that does not match the expected schema.
- The MCP server has requested you to elicit the missing information.
- You should inform user about the response and requested missing information from the MCP server.
- Then you should create a friendly and clear prompt for the user to respond to.
"""

ELICITATION_RESPONSE_PROMPT = """You are an elicitation assistant.

- Your task is to help the parse the user response to elicitation request.
- The user provided inputs that does not match the expected schema.
- The MCP server requested you to elicit the missing information.
- You informed user about the response and requested missing information from the MCP server.
- Based on that, user had the option to accept, decline or cancel the elicitation.
- If the user accepts, you should parse their response to match the expected schema.
- If user explicitly declines or dismisses, you should parse accordingly.
- Return only a JSON object containing the extracted fields, with correct types and values.
- Do not include any explanation or extra text, including backticks or markup.

If cancelled, return following JSON object exactly:

{
    "action": "cancel"
}

If declined, return JSON object with following structure:

{
    "action": "decline"
}

If accepted, return a JSON object with the following structure:

{
    "action": "accept",
    "content": "object with MCP server requested schema"
}
"""

MCP_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "alert": logging.CRITICAL,
    "emergency": logging.CRITICAL,
}


class MCPServer(pydantic.BaseModel):
    """Define an MCP server."""

    name: str
    connection_url: str
    connection_headers: dict | None = None


class MCPTool(pydantic.BaseModel):
    """Define a tool available on an MCP server."""

    name: str
    display_name: str
    title: str | None = None
    description: str | None = None
    input_schema: dict
    output_schema: dict | None = None
    annotations: ToolAnnotations | None = None
    server_name: str


class Status(enum.StrEnum):
    """Define the status of an MCP server operation."""

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
    langfuse_client : MonitoringClient
        client for monitoring and logging interactions, including Langfuse integration

    Attributes
    ----------
    mcp_servers : dict[str, MCPServer]
        mapping of MCP server names to their connection details
    mcp_server_tools : dict[str, list[MCPTool]]
        mapping of MCP server names to their available tools
    openai_client : OpenAIClient
        client for interacting with OpenAI API for tool calls
    tool_call_events : dict[str, dict]
        mapping of tool call identifiers to their events
    """

    def __init__(
        self: typing.Self, settings: Configurations, langfuse_client: MonitoringClient
    ) -> None:
        self.settings = settings
        self.langfuse_client = langfuse_client

        self.mcp_servers: dict[str, MCPServer] = {}
        self.mcp_server_tools: dict[str, list[MCPTool]] = {}

        self.openai_client = OpenAIClient(self.settings)

        self.tool_call_events: dict[str, dict] = {}

    async def add_mcp_server(
        self: typing.Self, server_name: str, server_url: str, server_headers: dict | None = None
    ) -> tuple[Status, list[str]]:
        """Add a new MCP server and retrieve its available tools.

        Parameters
        ----------
        server_name : str
            name of the MCP server to add
        server_url : str
            URL of the MCP server to add
        server_headers : dict | None, optional
            headers to include in requests to the MCP server, by default None

        Returns
        -------
        Status
            status of the addition operation
        list[str]
            list of tool names available on the added MCP server
        """
        LOGGER.info(
            f"Adding MCP server {server_name=} at {server_url=}.",
            extra={
                "event.group": "mcp",
                "event.type": "server_registry",
                "event.action": "add",
                "event.status": "started",
                "mcp.server.name": server_name,
                "mcp.server.url": server_url,
            },
        )

        server = MCPServer(
            name=server_name, connection_url=server_url, connection_headers=server_headers
        )

        transport = StreamableHttpTransport(
            server.connection_url, headers=server.connection_headers
        )

        try:
            async with Client(transport, auto_initialize=True) as client:
                server_tools = await client.list_tools()
        except ExceptionGroup:
            LOGGER.exception(
                f"Failed to add MCP server {server_name=} at {server_url=}.",
                extra={
                    "event.group": "mcp",
                    "event.type": "server_registry",
                    "event.action": "add",
                    "event.status": "failed",
                    "mcp.server.name": server_name,
                    "mcp.server.url": server_url,
                },
            )

            return Status.FAILURE, []
        except Exception:  # pylint: disable=broad-exception-caught
            LOGGER.exception(
                f"Failed to add MCP server {server_name=} at {server_url=}.",
                extra={
                    "event.group": "mcp",
                    "event.type": "server_registry",
                    "event.action": "add",
                    "event.status": "failed",
                    "mcp.server.name": server_name,
                    "mcp.server.url": server_url,
                },
            )

            return Status.FAILURE, []

        self.mcp_servers[server.name] = server

        processed_server_tools = [
            MCPTool(
                name=tool.name,
                display_name=get_display_name(tool),
                title=tool.title,
                description=tool.description,
                input_schema=tool.inputSchema,
                output_schema=tool.outputSchema,
                annotations=tool.annotations,
                server_name=server.name,
            )
            for tool in server_tools
        ]
        self.mcp_server_tools[server_name] = processed_server_tools

        LOGGER.info(
            f"Added MCP server {server_name=} with {len(processed_server_tools)} tools.",
            extra={
                "event.group": "mcp",
                "event.type": "server_registry",
                "event.action": "add",
                "event.status": "succeeded",
                "mcp.server.name": server_name,
                "mcp.server.url": server_url,
                "mcp.server.tool_count": len(processed_server_tools),
            },
        )

        return Status.SUCCESS, [tool.display_name for tool in processed_server_tools]

    def list_mcp_servers(self: typing.Self) -> dict[str, dict]:
        """List all added MCP servers.

        Returns
        -------
        dict[str, dict]
            mapping of MCP server names to their URLs
        """
        LOGGER.info(
            "Listing registered MCP servers.",
            extra={
                "event.group": "mcp",
                "event.type": "server_registry",
                "event.action": "list",
                "event.status": "started",
            },
        )

        servers = {
            server_name: server_details.model_dump()
            for server_name, server_details in self.mcp_servers.items()
        }

        LOGGER.info(
            f"Listed {len(servers)} registered MCP servers.",
            extra={
                "event.group": "mcp",
                "event.type": "server_registry",
                "event.action": "list",
                "event.status": "succeeded",
                "mcp.server.count": len(servers),
            },
        )

        return servers

    def remove_mcp_server(self: typing.Self, server_name: str) -> Status:
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
        LOGGER.info(
            f"Removing MCP server {server_name=}.",
            extra={
                "event.group": "mcp",
                "event.type": "server_registry",
                "event.action": "remove",
                "event.status": "started",
                "mcp.server.name": server_name,
            },
        )

        try:
            _ = self.mcp_servers.pop(server_name)
            _ = self.mcp_server_tools.pop(server_name)
        except KeyError:
            LOGGER.exception(
                f"Failed to remove MCP server {server_name=}.",
                extra={
                    "event.group": "mcp",
                    "event.type": "server_registry",
                    "event.action": "remove",
                    "event.status": "failed",
                    "mcp.server.name": server_name,
                },
            )

            return Status.FAILURE

        LOGGER.info(
            f"Removed MCP server {server_name=}.",
            extra={
                "event.group": "mcp",
                "event.type": "server_registry",
                "event.action": "remove",
                "event.status": "succeeded",
                "mcp.server.name": server_name,
            },
        )

        return Status.SUCCESS

    def list_mcp_server_tools(
        self: typing.Self, server_name: str
    ) -> tuple[Status, dict[str, str]]:
        """List all tools available on a specific MCP server.

        Parameters
        ----------
        server_name : str
            name of the MCP server to list tools for

        Returns
        -------
        Status
            status of the listing operation
        dict[str, str]
            mapping of tool names to their display names for the specified MCP server
        """
        LOGGER.info(
            f"Listing tools for MCP server {server_name=}.",
            extra={
                "event.group": "mcp",
                "event.type": "tool_catalog",
                "event.action": "list",
                "event.status": "started",
                "mcp.server.name": server_name,
            },
        )

        try:
            server_tools = self.mcp_server_tools[server_name]
        except KeyError:
            LOGGER.exception(
                f"MCP server {server_name=} does not exist.",
                extra={
                    "event.group": "mcp",
                    "event.type": "tool_catalog",
                    "event.action": "list",
                    "event.status": "failed",
                    "mcp.server.name": server_name,
                },
            )

            return Status.FAILURE, {}

        LOGGER.info(
            f"Listed {len(server_tools)} tools for MCP server {server_name=}.",
            extra={
                "event.group": "mcp",
                "event.type": "tool_catalog",
                "event.action": "list",
                "event.status": "succeeded",
                "mcp.server.name": server_name,
                "mcp.server.tool_count": len(server_tools),
            },
        )

        return Status.SUCCESS, {tool.name: tool.display_name for tool in server_tools}

    def describe_mcp_server_tool(
        self: typing.Self, server_name: str, tool_name: str
    ) -> tuple[Status, dict | None]:
        """Describe a specific tool available on an MCP server.

        Parameters
        ----------
        server_name : str
            name of the MCP server to describe the tool for
        tool_name : str
            name of the tool to describe

        Returns
        -------
        Status
            status of the description operation
        dict | None
            tool details if found, None otherwise
        """
        LOGGER.info(
            f"Describing tool {tool_name=} on MCP server {server_name=}.",
            extra={
                "event.group": "mcp",
                "event.type": "tool_catalog",
                "event.action": "describe",
                "event.status": "started",
                "mcp.server.name": server_name,
                "tool.name": tool_name,
            },
        )

        try:
            server_tools = self.mcp_server_tools[server_name]
        except KeyError:
            LOGGER.exception(
                f"MCP server {server_name=} does not exist.",
                extra={
                    "event.group": "mcp",
                    "event.type": "tool_catalog",
                    "event.action": "describe",
                    "event.status": "failed",
                    "mcp.server.name": server_name,
                    "tool.name": tool_name,
                },
            )

            return Status.FAILURE, None

        for tool in server_tools:
            if tool.name == tool_name:
                LOGGER.info(
                    f"Described tool {tool_name=} on MCP server {server_name=}.",
                    extra={
                        "event.group": "mcp",
                        "event.type": "tool_catalog",
                        "event.action": "describe",
                        "event.status": "succeeded",
                        "mcp.server.name": server_name,
                        "tool.name": tool_name,
                    },
                )

                return Status.SUCCESS, tool.model_dump()

        LOGGER.error(
            f"Tool {tool_name=} does not exist in MCP server {server_name=}.",
            extra={
                "event.group": "mcp",
                "event.type": "tool_catalog",
                "event.action": "describe",
                "event.status": "failed",
                "mcp.server.name": server_name,
                "tool.name": tool_name,
            },
        )

        return Status.FAILURE, None

    async def get_all_openai_functions(self: typing.Self) -> list[ChatCompletionToolParam]:
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

    async def sampling_handler(
        self: typing.Self,
        tool_call_id: str,
        context: RequestContext,
        parameters: CreateMessageRequestParams,
    ) -> CreateMessageResult | ErrorData:
        """Handle sampling requests for OpenAI API calls with MCP tools.

        Parameters
        ----------
        tool_call_id : str
            unique identifier for the tool call
        context : RequestContext
            request context containing information about the sampling request
        parameters : CreateMessageRequestParams
            parameters for the sampling request, including messages and customisations

        Returns
        -------
        CreateMessageResult | ErrorData
            result of the sampling request, either a message result or an error data
        """
        # TODO (@yarnabrina): find out how to use context
        # https://github.com/yarnabrina/learn-model-context-protocol/issues/4
        del context

        sampling_events: dict = {
            "server_messages": [
                (
                    message.content.text
                    if isinstance(message.content, TextContent)
                    else str(message.content)
                )
                for message in parameters.messages
            ]
        }

        if parameters.systemPrompt:
            sampling_events["server_instruction"] = parameters.systemPrompt

        openai_customisations: dict = {"max_completion_tokens": parameters.maxTokens}

        if (temperature := parameters.temperature) is not None:
            openai_customisations["temperature"] = temperature

        if (stop_sequences := parameters.stopSequences) is not None:
            openai_customisations["stop"] = stop_sequences

        messages = [
            ChatCompletionUserMessageParam(content=message, role="user")
            for message in sampling_events["server_messages"]
        ]

        available_openai_tools = await self.get_all_openai_functions()

        match parameters.includeContext:
            case "none":
                filtered_openai_tools = []
            case "thisServer":
                filtered_openai_tools = [
                    tool
                    for tool in available_openai_tools
                    if tool["function"]["name"].endswith(
                        self.tool_call_events[tool_call_id]["tool_name"]
                    )
                ]
            case "allServers":
                filtered_openai_tools = available_openai_tools
            case None:
                filtered_openai_tools = [
                    tool
                    for tool in available_openai_tools
                    if not tool["function"]["name"].endswith(
                        self.tool_call_events[tool_call_id]["tool_name"]
                    )
                ]

        with self.langfuse_client.start_as_current_observation(
            name=f"sampling for tool call {tool_call_id}",
            as_type="span",
            input=messages,
            end_on_exit=True,
        ) as sampling_monitoring:
            LOGGER.debug(
                f"Starting OpenAI sampling request for tool call {tool_call_id=}.",
                extra={
                    "event.group": "llm",
                    "event.type": "request",
                    "event.action": "request",
                    "event.status": "started",
                    "tool.call.id": tool_call_id,
                },
            )

            try:
                non_streaming_openai_response = (
                    await self.openai_client.get_non_streaming_openai_response(
                        messages,
                        system_prompt=parameters.systemPrompt,
                        tools=filtered_openai_tools,
                        openai_customisations=openai_customisations,
                    )
                )
            except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
                LOGGER.warning(
                    "Failed to get OpenAI response.",
                    exc_info=True,
                    extra={
                        "event.group": "llm",
                        "event.type": "request",
                        "event.action": "request",
                        "event.status": "failed",
                    },
                )

                sampling_monitoring.update(output=f"Failed to get OpenAI response: {error=}.")

                return ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to get OpenAI response: {error=}."
                )

            LOGGER.debug(
                f"Received response from OpenAI: {non_streaming_openai_response=}.",
                extra={
                    "event.group": "llm",
                    "event.type": "request",
                    "event.action": "request",
                    "event.status": "succeeded",
                },
            )

            if not (choices := non_streaming_openai_response.choices):
                LOGGER.warning(
                    "Received empty response from OpenAI.",
                    extra={
                        "event.group": "llm",
                        "event.type": "request",
                        "event.action": "request",
                        "event.status": "failed",
                    },
                )

                sampling_monitoring.update(output="Received empty response from OpenAI.")

                return ErrorData(
                    code=INTERNAL_ERROR, message="No choices returned from OpenAI API."
                )

            choice = choices[0]

            sampling_response_message = choice.message.content or ""

            sampling_monitoring.update(output=sampling_response_message)

        sampling_events["sampling_response"] = sampling_response_message

        self.tool_call_events[tool_call_id]["sampling_events"] = sampling_events

        return CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text=sampling_response_message),
            model=self.settings.language_model,
            stopReason=choice.finish_reason,
        )

    async def elicitation_handler(  # noqa: PLR0911
        self: typing.Self,
        tool_call_id: str,
        message: str,
        response_type: type | None,
        parameters: ElicitRequestParams,
        context: RequestContext,
    ) -> ElicitResult | ErrorData:
        """Handle elicitation requests for MCP tools.

        Parameters
        ----------
        tool_call_id : str
            unique identifier for the tool call
        message : str
            prompt to display to user
        response_type: type | None
            kind of response
        parameters : ElicitRequestParams
            parameters for the elicitation request, including message and requested schema
        context : RequestContext
            request context containing information about the elicitation request

        Returns
        -------
        ElicitResult | ErrorData
            result of the elicitation request, either an elicitation result or an error data
        """
        # TODO (@yarnabrina): find out how to use context
        # https://github.com/yarnabrina/learn-model-context-protocol/issues/4
        del context

        elicitation_events = {
            "server_message": message,
            "requested_schema": parameters.requestedSchema,
        }

        elicitation_request_messages = [
            ChatCompletionSystemMessageParam(content=ELICITATION_REQUEST_PROMPT, role="system"),
            ChatCompletionDeveloperMessageParam(
                content=elicitation_events["server_message"], role="developer"
            ),
            ChatCompletionDeveloperMessageParam(
                content=f"MCP Server Requested Schema: {elicitation_events['requested_schema']}",
                role="developer",
            ),
        ]

        with self.langfuse_client.start_as_current_observation(
            name=f"elicitation request for tool call {tool_call_id}",
            as_type="span",
            input=elicitation_request_messages,
            end_on_exit=True,
        ) as elicitation_request_monitoring:
            LOGGER.debug(
                f"Starting OpenAI elicitation request for tool call {tool_call_id=}.",
                extra={
                    "event.group": "llm",
                    "event.type": "request",
                    "event.action": "request",
                    "event.status": "started",
                    "tool.call.id": tool_call_id,
                },
            )

            try:
                elicitation_request_openai_response = (
                    await self.openai_client.get_non_streaming_openai_response(
                        elicitation_request_messages
                    )
                )
            except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
                LOGGER.warning(
                    "Failed to get OpenAI response.",
                    exc_info=True,
                    extra={
                        "event.group": "llm",
                        "event.type": "request",
                        "event.action": "request",
                        "event.status": "failed",
                    },
                )

                elicitation_request_monitoring.update(output="Failed to get OpenAI response.")

                return ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to get OpenAI response: {error=}."
                )

            LOGGER.debug(
                f"Received response from OpenAI: {elicitation_request_openai_response=}.",
                extra={
                    "event.group": "llm",
                    "event.type": "request",
                    "event.action": "request",
                    "event.status": "succeeded",
                },
            )

            if not (choices := elicitation_request_openai_response.choices):
                LOGGER.warning(
                    "Received empty response from OpenAI.",
                    extra={
                        "event.group": "llm",
                        "event.type": "request",
                        "event.action": "request",
                        "event.status": "failed",
                    },
                )

                elicitation_request_monitoring.update(
                    output="Received empty response from OpenAI."
                )

                return ErrorData(
                    code=INTERNAL_ERROR, message="No choices returned from OpenAI API."
                )

            elicitation_request_message = choices[0].message.content or ""

            elicitation_request_monitoring.update(output=elicitation_request_message)

        elicitation_events["elicitation_prompt"] = elicitation_request_message

        bot_response(elicitation_request_message)

        user_input = await user_prompt()

        elicitation_events["user_input"] = user_input

        elicitation_response_messages = [
            ChatCompletionSystemMessageParam(content=ELICITATION_RESPONSE_PROMPT, role="system"),
            ChatCompletionDeveloperMessageParam(
                content=elicitation_events["server_message"], role="developer"
            ),
            ChatCompletionDeveloperMessageParam(
                content=f"MCP Server Requested Schema: {elicitation_events['requested_schema']}",
                role="developer",
            ),
            ChatCompletionAssistantMessageParam(
                role="assistant", content=elicitation_request_message
            ),
            ChatCompletionUserMessageParam(content=user_input, role="user"),
        ]

        with self.langfuse_client.start_as_current_observation(
            name=f"elicitation response for tool call {tool_call_id=}",
            as_type="span",
            input=elicitation_response_messages,
            end_on_exit=True,
        ) as elicitation_response_monitoring:
            LOGGER.debug(
                f"Starting OpenAI elicitation response request for tool call {tool_call_id=}.",
                extra={
                    "event.group": "llm",
                    "event.type": "request",
                    "event.action": "request",
                    "event.status": "started",
                    "tool.call.id": tool_call_id,
                },
            )

            try:
                elicitation_response_openai_response = (
                    await self.openai_client.get_non_streaming_openai_response(
                        elicitation_response_messages
                    )
                )
            except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
                LOGGER.warning(
                    "Failed to get OpenAI response.",
                    exc_info=True,
                    extra={
                        "event.group": "llm",
                        "event.type": "request",
                        "event.action": "request",
                        "event.status": "failed",
                    },
                )

                elicitation_response_monitoring.update(output="Failed to get OpenAI response.")

                return ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to get OpenAI response: {error=}."
                )

            LOGGER.debug(
                f"Received response from OpenAI: {elicitation_response_openai_response=}.",
                extra={
                    "event.group": "llm",
                    "event.type": "request",
                    "event.action": "request",
                    "event.status": "succeeded",
                },
            )

            if not (choices := elicitation_response_openai_response.choices):
                LOGGER.warning(
                    "Received empty response from OpenAI.",
                    extra={
                        "event.group": "llm",
                        "event.type": "request",
                        "event.action": "request",
                        "event.status": "failed",
                    },
                )

                elicitation_response_monitoring.update(
                    output="Received empty response from OpenAI."
                )

                return ErrorData(
                    code=INTERNAL_ERROR, message="No choices returned from OpenAI API."
                )

            try:
                elicitation_response_message = json.loads(choices[0].message.content or "{}")
            except json.JSONDecodeError as error:
                LOGGER.warning("Failed to parse elicitation response as JSON.", exc_info=True)

                elicitation_response_monitoring.update(
                    output=f"Failed to parse elicitation response as JSON: {error=}."
                )

                return ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to parse elicitation response: {error=}."
                )

            elicitation_events["elicitation_correction"] = elicitation_response_message

            elicitation_response_monitoring.update(output=elicitation_response_message)

        self.tool_call_events[tool_call_id]["elicitation_events"] = elicitation_events

        if (
            response_type is None
            or not isinstance(elicitation_response_message, dict)
            or not {"action", "content"}.issubset(elicitation_response_message.keys())
        ):
            LOGGER.warning("Elicitation response is unexpected, returning without parsing.")

            return elicitation_response_message

        match (action := elicitation_response_message["action"]):
            case "cancel" | "decline":
                return ElicitResult(action=action)
            case "accept":
                return ElicitResult(
                    action="accept",
                    content=response_type(value=elicitation_response_message["content"]),
                )
            case _:
                LOGGER.error("Elicitation response is unacceptable.")

                return ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Unacceptable elicitation response: {elicitation_response_message=}.",
                )

    @staticmethod
    async def logging_handler(
        tool_call_id: str, parameters: LoggingMessageNotificationParams
    ) -> None:
        """Handle logging requests from MCP tools.

        Parameters
        ----------
        tool_call_id : str
            unique identifier for the tool call
        parameters : LoggingMessageNotificationParams
            parameters for the logging request, including log level and message data
        """
        log_level = MCP_LOG_LEVELS[parameters.level]

        log_message = str(parameters.data)
        if (logger := parameters.logger) is not None:
            log_message += f" ({logger})"

        LOGGER.log(
            log_level,
            log_message,
            extra={
                "event.group": "mcp",
                "event.type": "remote_log",
                "event.action": "receive",
                "event.status": "succeeded",
                "tool.call.id": tool_call_id,
                "mcp.remote.log.level": parameters.level,
                "mcp.remote.log.logger": parameters.logger,
                "mcp.remote.log.data": parameters.data,
                "mcp.remote.log.data.msg": parameters.data.get("msg"),
                "mcp.remote.log.data.extra": parameters.data.get("extra"),
            },
        )

    @staticmethod
    async def progress_handler(
        tool_call_id: str, progress: float, total: float | None, message: str | None
    ) -> None:
        """Report progress for MCP tools.

        Parameters
        ----------
        tool_call_id : str
            unique identifier for the tool call
        progress : float
            current progress value
        total : float | None
            total progress value
        message : str | None
            optional message to accompany the progress report
        """
        completion = f"{progress}"

        if total is not None:
            completion += f"/{total}"

            if total != 0:
                percentage = 100 * (progress / total)
                completion += f" ({percentage:.2f}%)"

        progress_message = f"Progress of {tool_call_id}: {completion}."

        if message:
            progress_message += f" {message}."

        LOGGER.info(
            progress_message,
            extra={
                "event.group": "mcp",
                "event.type": "progress",
                "event.action": "receive",
                "event.status": "in_progress",
                "tool.call.id": tool_call_id,
                "progress.current": progress,
                "progress.total": total,
                "progress.message": message,
            },
        )

        bot_response(progress_message)

    async def execute_tool_call(  # noqa: PLR0911
        self: typing.Self, tool_call_id: str, tool_name: str, arguments: dict
    ) -> str:
        """Execute a tool call on an MCP server.

        Parameters
        ----------
        tool_call_id : str
            unique identifier for the tool call
        tool_name : str
            name of the tool to call, formatted as "mcp-{server_name}-{tool_name}"
        arguments : dict
            arguments to pass to the tool call

        Returns
        -------
        str
            JSON string containing the result of the tool call or an error message
        """
        LOGGER.debug(
            f"Starting tool call {tool_name=} with the following parameters: {arguments=}.",
            extra={
                "event.group": "tool",
                "event.type": "remote_call",
                "event.action": "execute",
                "event.status": "started",
                "tool.call.id": tool_call_id,
                "tool.name": tool_name,
            },
        )

        if not tool_name.startswith("mcp-"):
            LOGGER.warning(
                f"Unknown MCP tool {tool_name=}.",
                extra={
                    "event.group": "tool",
                    "event.type": "remote_call",
                    "event.action": "execute",
                    "event.status": "failed",
                    "tool.call.id": tool_call_id,
                    "tool.name": tool_name,
                },
            )

            return json.dumps({"error": f"Unknown MCP tool {tool_name}."})

        _, server_name, actual_tool_name = tool_name.split(sep="-", maxsplit=2)

        if server_name not in self.mcp_servers:
            LOGGER.warning(
                f"Unknown MCP connection {server_name=} for tool call {tool_name=}.",
                extra={
                    "event.group": "tool",
                    "event.type": "remote_call",
                    "event.action": "execute",
                    "event.status": "failed",
                    "tool.call.id": tool_call_id,
                    "tool.name": actual_tool_name,
                    "mcp.server.name": server_name,
                },
            )

            return json.dumps({"error": f"Unknown MCP connection {server_name}."})

        server = self.mcp_servers[server_name]

        self.tool_call_events[tool_call_id] = {
            "server_name": server_name,
            "server_url": server.connection_url,
            "tool_name": actual_tool_name,
            "arguments": arguments,
        }

        LOGGER.debug(
            f"Resolved tool call {actual_tool_name=} for MCP server {server_name=} "
            f"({server.connection_url=}) with the following parameters: {arguments=}."
        )

        if self.settings.trace:
            trace_tool_input(actual_tool_name, arguments)

        sampling_handler = (
            functools.partial(self.sampling_handler, tool_call_id)
            if self.settings.sampling
            else None
        )
        sampling_capabilities_declaration = (
            SamplingCapability(tools=SamplingToolsCapability()) if self.settings.sampling else None
        )
        elicitation_handler = (
            functools.partial(self.elicitation_handler, tool_call_id)
            if self.settings.elicitation
            else None
        )
        logging_handler = (
            functools.partial(self.logging_handler, tool_call_id)
            if self.settings.logging
            else None
        )
        progress_handler = (
            functools.partial(self.progress_handler, tool_call_id)
            if self.settings.progress
            else None
        )

        transport = StreamableHttpTransport(
            server.connection_url, headers=server.connection_headers
        )

        try:
            async with Client(
                transport,
                sampling_handler=sampling_handler,
                sampling_capabilities=sampling_capabilities_declaration,
                elicitation_handler=elicitation_handler,
                log_handler=logging_handler,
            ) as client:
                tool_result = await client.call_tool(
                    actual_tool_name, arguments=arguments, progress_handler=progress_handler
                )
        except ExceptionGroup:
            LOGGER.warning(
                f"Failed tool call to {actual_tool_name=} of MCP server {server_name=}.",
                exc_info=True,
                extra={
                    "event.group": "tool",
                    "event.type": "remote_call",
                    "event.action": "execute",
                    "event.status": "failed",
                    "tool.call.id": tool_call_id,
                    "tool.name": actual_tool_name,
                    "mcp.server.name": server_name,
                    "mcp.server.url": server.connection_url,
                },
            )

            return json.dumps({"error": f"Failed tool call to {actual_tool_name}."})
        except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
            LOGGER.warning(
                f"Failed tool call to {actual_tool_name=} of MCP server {server_name=}.",
                exc_info=True,
                extra={
                    "event.group": "tool",
                    "event.type": "remote_call",
                    "event.action": "execute",
                    "event.status": "failed",
                    "tool.call.id": tool_call_id,
                    "tool.name": actual_tool_name,
                    "mcp.server.name": server_name,
                    "mcp.server.url": server.connection_url,
                },
            )

            return json.dumps({"error": f"Failed tool call to {actual_tool_name}: {error}."})

        LOGGER.debug(
            f"Received response from tool {actual_tool_name=} "
            f"for tool call {tool_call_id=} "
            f"from MCP server {server_name=} ({server.connection_url=}) "
            f"as follows: {tool_result=}.\n",
            extra={
                "event.group": "tool",
                "event.type": "remote_call",
                "event.action": "execute",
                "event.status": "succeeded",
                "tool.call.id": tool_call_id,
                "tool.name": actual_tool_name,
                "mcp.server.name": server_name,
                "mcp.server.url": server.connection_url,
            },
        )

        if self.settings.trace:
            trace_tool_output(actual_tool_name, dataclasses.asdict(tool_result))

        if tool_result.is_error:
            error_message = "".join(
                content.text for content in tool_result.content if isinstance(content, TextContent)
            )

            LOGGER.warning(
                f"Tool call {tool_name=} failed with {arguments=}: {error_message=}.",
                extra={
                    "event.group": "tool",
                    "event.type": "remote_call",
                    "event.action": "execute",
                    "event.status": "failed",
                    "tool.call.id": tool_call_id,
                    "tool.name": actual_tool_name,
                    "mcp.server.name": server_name,
                    "mcp.server.url": server.connection_url,
                },
            )

            return json.dumps(
                {"error": f"Tool call {tool_name} failed with {arguments}: {error_message}."}
            )

        if (structured_result := tool_result.structured_content) is not None:
            return json.dumps(structured_result)

        return json.dumps([element.model_dump() for element in tool_result.content])


__all__ = ["MCPClient", "MCPServer", "MCPTool", "OpenAIFunctionDefinition", "Status"]
