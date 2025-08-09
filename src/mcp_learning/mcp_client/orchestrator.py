"""Implement client-side logic for MCP server management."""

import collections.abc
import enum
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
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_message_function_tool_call_param import (
    ChatCompletionMessageFunctionToolCallParam,
    Function,
)
from openai.types.shared_params import FunctionDefinition

from .configurations import Configurations
from .console import bot_response, user_prompt
from .llm import OpenAIClient

LOGGER = logging.getLogger(__name__)

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
    """Define the status of an MCP server operation."""

    SUCCESS = "success"
    FAILURE = "failure"


class OpenAIFunctionDefinition(pydantic.BaseModel):
    """Define an OpenAI API compatible function definition for MCP tools."""

    name: str
    description: str | None = None
    parameters: dict | None = None


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

    async def add_mcp_server(
        self: "MCPClient", server_name: str, server_url: str
    ) -> tuple[Status, list[str]]:
        """Add a new MCP server and retrieve its available tools.

        Parameters
        ----------
        server_name : str
            name of the MCP server to add
        server_url : str
            URL of the MCP server to add

        Returns
        -------
        Status
            status of the addition operation
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
        except ExceptionGroup:
            LOGGER.exception(f"Failed to add MCP server {server_name} at {server_url}.")

            _ = self.mcp_servers.pop(server_name)

            return Status.FAILURE, []
        except Exception:  # pylint: disable=broad-exception-caught
            LOGGER.exception(f"Failed to add MCP server {server_name} at {server_url}.")

            _ = self.mcp_servers.pop(server_name)

            return Status.FAILURE, []

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

        return Status.SUCCESS, [tool.display_name for tool in processed_server_tools]

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
    ) -> tuple[Status, MCPTool | None]:
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
        MCPTool | None
            tool details if found, None otherwise
        """
        try:
            server_tools = self.mcp_server_tools[server_name]
        except KeyError:
            LOGGER.exception(f"MCP server {server_name} does not exist.")

            return Status.FAILURE, None

        for tool in server_tools:
            if tool.name == tool_name:
                return Status.SUCCESS, tool

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
        self: "MCPClient", context: RequestContext, parameters: CreateMessageRequestParams
    ) -> CreateMessageResult | ErrorData:
        """Handle sampling requests for OpenAI API calls with MCP tools.

        Parameters
        ----------
        context : RequestContext
            request context containing information about the sampling request
        parameters : CreateMessageRequestParams
            parameters for the sampling request, including messages and customisations

        Returns
        -------
        CreateMessageResult | ErrorData
            result of the sampling request, either a message result or an error data
        """
        # TODO (@yarnabrina): find out to use context
        # https://github.com/yarnabrina/learn-model-context-protocol/issues/4
        del context

        openai_customisations: dict = {"max_completion_tokens": parameters.maxTokens}

        if (temperature := parameters.temperature) is not None:
            openai_customisations["temperature"] = temperature

        if (stop_sequences := parameters.stopSequences) is not None:
            openai_customisations["stop"] = stop_sequences

        messages = [
            ChatCompletionUserMessageParam(
                content=(
                    message.content.text
                    if isinstance(message.content, TextContent)
                    else str(message.content)
                ),
                role="user",
            )
            for message in parameters.messages
        ]

        available_openai_tools = await self.get_all_openai_functions()

        # TODO (@yarnabrina): find out to use parameters.includeContext
        # https://github.com/yarnabrina/learn-model-context-protocol/issues/5
        filtered_openai_tools = available_openai_tools

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

            return ErrorData(
                code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                message=f"Failed to get OpenAI response: {error}.",
            )

        LOGGER.debug(f"Received response from OpenAI: {non_streaming_openai_response}.")

        if not (choices := non_streaming_openai_response.choices):
            LOGGER.warning("Received empty response from OpenAI.")

            return ErrorData(
                code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                message="No choices returned from OpenAI API.",
            )

        choice = choices[0]

        return CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text=choice.message.content or ""),
            model=self.settings.language_model,
            stopReason=choice.finish_reason,
        )

    async def elicitation_handler(
        self: "MCPClient", context: RequestContext, parameters: ElicitRequestParams
    ) -> ElicitResult | ErrorData:
        """Handle elicitation requests for MCP tools.

        Parameters
        ----------
        context : RequestContext
            request context containing information about the elicitation request
        parameters : ElicitRequestParams
            parameters for the elicitation request, including message and requested schema

        Returns
        -------
        ElicitResult | ErrorData
            result of the elicitation request, either an elicitation result or an error data
        """
        # TODO (@yarnabrina): find out to use context
        # https://github.com/yarnabrina/learn-model-context-protocol/issues/4
        del context

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

        try:
            elicitation_request_openai_response = (
                await self.openai_client.get_non_streaming_openai_response(
                    elicitation_request_messages
                )
            )
        except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
            LOGGER.warning("Failed to get OpenAI response.", exc_info=True)

            return ErrorData(
                code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                message=f"Failed to get OpenAI response: {error}.",
            )

        LOGGER.debug(f"Received response from OpenAI: {elicitation_request_openai_response}.")

        if not (choices := elicitation_request_openai_response.choices):
            LOGGER.warning("Received empty response from OpenAI.")

            return ErrorData(
                code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                message="No choices returned from OpenAI API.",
            )

        elicitation_request_message = choices[0].message.content or ""

        bot_response(elicitation_request_message)

        user_input = user_prompt()

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

        try:
            elicitation_response_openai_response = (
                await self.openai_client.get_non_streaming_openai_response(
                    elicitation_response_messages
                )
            )
        except Exception as error:  # noqa: BLE001, pylint: disable=broad-exception-caught
            LOGGER.warning("Failed to get OpenAI response.", exc_info=True)

            return ErrorData(
                code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                message=f"Failed to get OpenAI response: {error}.",
            )

        LOGGER.debug(f"Received response from OpenAI: {elicitation_response_openai_response}.")

        if not (choices := elicitation_response_openai_response.choices):
            LOGGER.warning("Received empty response from OpenAI.")

            return ErrorData(
                code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                message="No choices returned from OpenAI API.",
            )

        try:
            elicitation_response_message = json.loads(choices[0].message.content or "{}")
        except json.JSONDecodeError as error:
            LOGGER.warning("Failed to parse elicitation response as JSON.", exc_info=True)

            return ErrorData(
                code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                message=f"Failed to parse elicitation response: {error}.",
            )

        return elicitation_response_message

    async def logging_handler(
        self: "MCPClient", parameters: LoggingMessageNotificationParams
    ) -> None:
        """Handle logging requests from MCP tools.

        Parameters
        ----------
        parameters : LoggingMessageNotificationParams
            parameters for the logging request, including log level and message data
        """
        LOGGER.log(MCP_LOG_LEVELS[parameters.level], parameters.data)

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

        LOGGER.debug(
            f"Calling tool {actual_tool_name} "
            f"from MCP server {server_name} ({server_url}) "
            f"with following parameters: {arguments}."
        )

        try:
            async with streamablehttp_client(server_url) as (  # noqa: SIM117
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(
                    read_stream,
                    write_stream,
                    sampling_callback=self.sampling_handler,
                    elicitation_callback=self.elicitation_handler,
                    logging_callback=self.logging_handler,
                ) as session:
                    await session.initialize()

                    tool_result = await session.call_tool(actual_tool_name, arguments=arguments)
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
            f"of MCP server {server_name} ({server_url}) "
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


class OpenAIOrchestrator:
    """Define an orchestrator for handling OpenAI API calls with MCP tools.

    Parameters
    ----------
    settings : Configurations
        language model configurations containing API keys and customisations
    system_prompt : str | None, optional
        initial system prompt to set the context, by default None
    mcp_client : MCPClient, optional
        client for managing MCP servers and their tools, by default None

    Attributes
    ----------
    openai_client : OpenAIClient
        client for interacting with OpenAI API for tool calls
    conversation_history : list[ChatCompletionMessageParam]
        history of conversation messages for the OpenAI API
    """

    def __init__(
        self: "OpenAIOrchestrator",
        settings: Configurations,
        system_prompt: str | None = None,
        mcp_client: MCPClient | None = None,
    ) -> None:
        self.settings = settings
        self.system_prompt = system_prompt
        self.mcp_client = mcp_client

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
        available_openai_tools = (
            None if self.mcp_client is None else await self.mcp_client.get_all_openai_functions()
        )

        chat_completion = self.openai_client.get_streaming_openai_response(
            self.conversation_history,
            system_prompt=self.system_prompt,
            tools=available_openai_tools,
        )

        tool_calls: dict[int, ChatCompletionMessageFunctionToolCallParam] = {}
        async for chunk in chat_completion:
            if not chunk.choices:
                continue

            chunk_response = chunk.choices[0]

            for tool_call in chunk_response.delta.tool_calls or []:
                index = tool_call.index

                if index not in tool_calls:
                    tool_calls[index] = ChatCompletionMessageFunctionToolCallParam(
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

    async def process_user_message(  # noqa: C901
        self: "OpenAIOrchestrator", user_message: str
    ) -> collections.abc.AsyncGenerator[str]:
        """Process a user message and generate a response using OpenAI API.

        Parameters
        ----------
        user_message : str
            new message from the user to process

        Yields
        ------
        str
            token content from the OpenAI API response
        """
        self.conversation_history.append({"role": "user", "content": user_message})

        assistant_message = ""
        async for (
            finish_reason_delta,
            assistant_message_token,
            assistant_tool_calls_delta,
        ) in self.call_openai():
            if assistant_message_token:
                assistant_message += assistant_message_token

                yield assistant_message_token

            if finish_reason_delta:
                finish_reason = finish_reason_delta
                assistant_tool_calls = assistant_tool_calls_delta

                yield "\n"

                break
        else:
            yield "\n"

        while finish_reason == "tool_calls":
            self.conversation_history.append(
                ChatCompletionAssistantMessageParam(
                    role="assistant", content=assistant_message, tool_calls=assistant_tool_calls
                )
            )

            LOGGER.debug(f"Identified tool calls: {assistant_tool_calls}.")

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

            assistant_message = ""
            async for (
                finish_reason_delta,
                assistant_message_token,
                assistant_tool_calls_delta,
            ) in self.call_openai():
                if assistant_message_token:
                    assistant_message += assistant_message_token

                    yield assistant_message_token

                if finish_reason_delta:
                    finish_reason = finish_reason_delta
                    assistant_tool_calls = assistant_tool_calls_delta

                    yield "\n"

                    break
            else:
                yield "\n"

        self.conversation_history.append({"role": "assistant", "content": assistant_message})
