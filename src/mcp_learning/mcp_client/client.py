"""Implement client-side logic for MCP server management."""

import enum
import functools
import http
import json
import logging

import pydantic
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.context import RequestContext
from mcp.shared.metadata_utils import get_display_name
from mcp.types import (
    CreateMessageRequestParams,
    CreateMessageResult,
    ElicitRequestParams,
    ElicitResult,
    ErrorData,
    LoggingMessageNotificationParams,
    TextContent,
    ToolAnnotations,
)
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params import FunctionDefinition

from .llm import OpenAIClient
from .utils import Configurations, MonitoringClient, bot_response, user_prompt

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
        self: "MCPClient", settings: Configurations, langfuse_client: MonitoringClient
    ) -> None:
        self.settings = settings
        self.langfuse_client = langfuse_client

        self.mcp_servers: dict[str, MCPServer] = {}
        self.mcp_server_tools: dict[str, list[MCPTool]] = {}

        self.openai_client = OpenAIClient(self.settings)

        self.tool_call_events: dict[str, dict] = {}

    async def add_mcp_server(
        self: "MCPClient", server_name: str, server_url: str, server_headers: dict | None = None
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
        server = MCPServer(
            name=server_name, connection_url=server_url, connection_headers=server_headers
        )

        try:
            async with streamablehttp_client(  # noqa: SIM117
                server.connection_url, headers=server.connection_headers
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    server_tools = await session.list_tools()
        except ExceptionGroup:
            LOGGER.exception(f"Failed to add MCP server {server_name} at {server_url}.")

            return Status.FAILURE, []
        except Exception:  # pylint: disable=broad-exception-caught
            LOGGER.exception(f"Failed to add MCP server {server_name} at {server_url}.")

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
            for tool in server_tools.tools
        ]
        self.mcp_server_tools[server_name] = processed_server_tools

        return Status.SUCCESS, [tool.display_name for tool in processed_server_tools]

    def list_mcp_servers(self: "MCPClient") -> dict[str, dict]:
        """List all added MCP servers.

        Returns
        -------
        dict[str, dict]
            mapping of MCP server names to their URLs
        """
        return {
            server_name: server_details.model_dump()
            for server_name, server_details in self.mcp_servers.items()
        }

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
        except KeyError:
            LOGGER.exception(f"Failed to remove MCP server {server_name}.")

            return Status.FAILURE

        return Status.SUCCESS

    def list_mcp_server_tools(
        self: "MCPClient", server_name: str
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
        try:
            server_tools = self.mcp_server_tools[server_name]
        except KeyError:
            LOGGER.exception(f"MCP server {server_name} does not exist.")

            return Status.FAILURE, {}

        return Status.SUCCESS, {tool.name: tool.display_name for tool in server_tools}

    def describe_mcp_server_tool(
        self: "MCPClient", server_name: str, tool_name: str
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
        try:
            server_tools = self.mcp_server_tools[server_name]
        except KeyError:
            LOGGER.exception(f"MCP server {server_name} does not exist.")

            return Status.FAILURE, None

        for tool in server_tools:
            if tool.name == tool_name:
                return Status.SUCCESS, tool.model_dump()

        LOGGER.error(f"Tool {tool_name} does not exist in MCP server {server_name}.")

        return Status.FAILURE, None

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

    async def sampling_handler(
        self: "MCPClient",
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
                LOGGER.warning("Failed to get OpenAI response.", exc_info=True)

                sampling_monitoring.update(output=f"Failed to get OpenAI response: {error}.")

                return ErrorData(
                    code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                    message=f"Failed to get OpenAI response: {error}.",
                )

            LOGGER.debug(f"Received response from OpenAI: {non_streaming_openai_response}.")

            if not (choices := non_streaming_openai_response.choices):
                LOGGER.warning("Received empty response from OpenAI.")

                sampling_monitoring.update(output="Received empty response from OpenAI.")

                return ErrorData(
                    code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                    message="No choices returned from OpenAI API.",
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

    async def elicitation_handler(
        self: "MCPClient",
        tool_call_id: str,
        context: RequestContext,
        parameters: ElicitRequestParams,
    ) -> ElicitResult | ErrorData:
        """Handle elicitation requests for MCP tools.

        Parameters
        ----------
        tool_call_id : str
            unique identifier for the tool call
        context : RequestContext
            request context containing information about the elicitation request
        parameters : ElicitRequestParams
            parameters for the elicitation request, including message and requested schema

        Returns
        -------
        ElicitResult | ErrorData
            result of the elicitation request, either an elicitation result or an error data
        """
        # TODO (@yarnabrina): find out how to use context
        # https://github.com/yarnabrina/learn-model-context-protocol/issues/4
        del context

        elicitation_events = {
            "server_message": parameters.message,
            "requested_schema": parameters.requestedSchema,
        }

        elicitation_request_messages = [
            ChatCompletionSystemMessageParam(content=ELICITATION_REQUEST_PROMPT, role="system"),
            ChatCompletionAssistantMessageParam(
                role="assistant",
                content="\n".join(
                    [
                        f"MCP Server Message: {parameters.message}",
                        f"MCP Server Requested Schema: {parameters.requestedSchema}",
                    ]
                ),
            ),
        ]

        with self.langfuse_client.start_as_current_observation(
            name=f"elicitation request for tool call {tool_call_id}",
            as_type="span",
            input=elicitation_request_messages,
            end_on_exit=True,
        ) as elicitation_request_monitoring:
            try:
                elicitation_request_openai_response = (
                    await self.openai_client.get_non_streaming_openai_response(
                        elicitation_request_messages
                    )
                )
            except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
                LOGGER.warning("Failed to get OpenAI response.", exc_info=True)

                elicitation_request_monitoring.update(output="Failed to get OpenAI response.")

                return ErrorData(
                    code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                    message=f"Failed to get OpenAI response: {error}.",
                )

            LOGGER.debug(f"Received response from OpenAI: {elicitation_request_openai_response}.")

            if not (choices := elicitation_request_openai_response.choices):
                LOGGER.warning("Received empty response from OpenAI.")

                elicitation_request_monitoring.update(
                    output="Received empty response from OpenAI."
                )

                return ErrorData(
                    code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                    message="No choices returned from OpenAI API.",
                )

            elicitation_request_message = choices[0].message.content or ""

            elicitation_request_monitoring.update(output=elicitation_request_message)

        elicitation_events["elicitation_prompt"] = elicitation_request_message

        bot_response(elicitation_request_message)

        user_input = await user_prompt()

        elicitation_events["user_input"] = user_input

        elicitation_response_messages = [
            ChatCompletionSystemMessageParam(content=ELICITATION_RESPONSE_PROMPT, role="system"),
            ChatCompletionAssistantMessageParam(
                role="assistant",
                content="\n".join(
                    [
                        f"MCP Server Message: {parameters.message}",
                        f"MCP Server Requested Schema: {parameters.requestedSchema}",
                    ]
                ),
            ),
            ChatCompletionAssistantMessageParam(
                role="assistant", content=elicitation_request_message
            ),
            ChatCompletionUserMessageParam(content=user_input, role="user"),
        ]

        with self.langfuse_client.start_as_current_observation(
            name=f"elicitation response for tool call {tool_call_id}",
            as_type="span",
            input=elicitation_response_messages,
            end_on_exit=True,
        ) as elicitation_response_monitoring:
            try:
                elicitation_response_openai_response = (
                    await self.openai_client.get_non_streaming_openai_response(
                        elicitation_response_messages
                    )
                )
            except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
                LOGGER.warning("Failed to get OpenAI response.", exc_info=True)

                elicitation_response_monitoring.update(output="Failed to get OpenAI response.")

                return ErrorData(
                    code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                    message=f"Failed to get OpenAI response: {error}.",
                )

            LOGGER.debug(f"Received response from OpenAI: {elicitation_response_openai_response}.")

            if not (choices := elicitation_response_openai_response.choices):
                LOGGER.warning("Received empty response from OpenAI.")

                elicitation_response_monitoring.update(
                    output="Received empty response from OpenAI."
                )

                return ErrorData(
                    code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                    message="No choices returned from OpenAI API.",
                )

            try:
                elicitation_response_message = json.loads(choices[0].message.content or "{}")
            except json.JSONDecodeError as error:
                LOGGER.warning("Failed to parse elicitation response as JSON.", exc_info=True)

                elicitation_response_monitoring.update(
                    output=f"Failed to parse elicitation response as JSON: {error}."
                )

                return ErrorData(
                    code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                    message=f"Failed to parse elicitation response: {error}.",
                )

            elicitation_events["elicitation_correction"] = elicitation_response_message

            elicitation_response_monitoring.update(output=elicitation_response_message)

        self.tool_call_events[tool_call_id]["elicitation_events"] = elicitation_events

        return elicitation_response_message

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
        LOGGER.log(
            MCP_LOG_LEVELS[parameters.level], parameters.data, extra={"tool_call_id": tool_call_id}
        )

    @staticmethod
    async def progress_handler(
        tool_call_id: str, progress: float, total: float | None = None, message: str | None = None
    ) -> None:
        """Report progress for MCP tools.

        Parameters
        ----------
        tool_call_id : str
            unique identifier for the tool call
        progress : float
            current progress value
        total : float | None, optional
            total progress value, by default None
        message : str | None, optional
            optional message to accompany the progress report, by default None
        """
        completion = f"{progress}"
        if total is not None:
            completion += f"/{total}"

        progress_message = f"Progress of {tool_call_id}: {completion}."

        if message:
            progress_message += f" {message}."

        bot_response(progress_message)

    async def execute_tool_call(  # noqa: PLR0911
        self: "MCPClient", tool_call_id: str, tool_name: str, arguments: dict
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
        if not tool_name.startswith("mcp-"):
            return json.dumps({"error": f"Unknown MCP tool {tool_name}."})

        _, server_name, actual_tool_name = tool_name.split(sep="-", maxsplit=2)

        if server_name not in self.mcp_servers:
            return json.dumps({"error": f"Unknown MCP connection {server_name}."})

        server = self.mcp_servers[server_name]

        self.tool_call_events[tool_call_id] = {
            "server_name": server_name,
            "server_url": server.connection_url,
            "tool_name": actual_tool_name,
            "arguments": arguments,
        }

        LOGGER.debug(
            f"Calling tool {actual_tool_name} "
            f"as part of tool call {tool_call_id} "
            f"from MCP server {server_name} ({server.connection_url}) "
            f"with following parameters: {arguments}."
        )

        sampling_handler = (
            functools.partial(self.sampling_handler, tool_call_id)
            if self.settings.sampling
            else None
        )
        elicitation_handler = (
            functools.partial(self.elicitation_handler, tool_call_id)
            if self.settings.sampling
            else None
        )
        logging_handler = (
            functools.partial(self.logging_handler, tool_call_id)
            if self.settings.sampling
            else None
        )
        progress_handler = (
            functools.partial(self.progress_handler, tool_call_id)
            if self.settings.sampling
            else None
        )

        try:
            async with streamablehttp_client(  # noqa: SIM117
                server.connection_url, headers=server.connection_headers
            ) as (read_stream, write_stream, _):
                async with ClientSession(
                    read_stream,
                    write_stream,
                    sampling_callback=sampling_handler,
                    elicitation_callback=elicitation_handler,
                    logging_callback=logging_handler,
                ) as session:
                    await session.initialize()

                    tool_result = await session.call_tool(
                        actual_tool_name, arguments=arguments, progress_callback=progress_handler
                    )
        except ExceptionGroup:
            LOGGER.warning(
                f"Failed tool call to {actual_tool_name} of MCP server {server_name}.",
                exc_info=True,
            )

            return json.dumps({"error": f"Failed tool call to {actual_tool_name}."})
        except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
            LOGGER.warning(
                f"Failed tool call to {actual_tool_name} of MCP server {server_name}.",
                exc_info=True,
            )

            return json.dumps({"error": f"Failed tool call to {actual_tool_name}: {error}."})

        LOGGER.debug(
            f"Received response from tool {actual_tool_name} "
            f"as part of tool call {tool_call_id} "
            f"of MCP server {server_name} ({server.connection_url}) "
            f"as following: {tool_result}.\n"
        )

        if tool_result.isError:
            error_message = "".join(
                content.text for content in tool_result.content if isinstance(content, TextContent)
            )

            LOGGER.warning(f"Failed tool call to {tool_name=} with {arguments=}: {error_message}.")

            return json.dumps(
                {
                    "error": (
                        f"Failed tool call to {tool_name=} with {arguments=}: {error_message}."
                    )
                }
            )

        if (structured_result := tool_result.structuredContent) is not None:
            return json.dumps(structured_result)

        return json.dumps([element.model_dump() for element in tool_result.content])


__all__ = ["MCPClient", "MCPServer", "MCPTool", "OpenAIFunctionDefinition", "Status"]
