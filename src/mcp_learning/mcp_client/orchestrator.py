"""Implement orchestrator logic for managing OpenAI API calls with MCP tools."""

import collections.abc
import json
import logging

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
)
from openai.types.chat.chat_completion_message_function_tool_call_param import (
    ChatCompletionMessageFunctionToolCallParam,
    Function,
)

from .client import MCPClient
from .llm import OpenAIClient
from .utils import Configurations, MonitoringClient

LOGGER = logging.getLogger(__name__)


class OpenAIOrchestrator:
    """Define an orchestrator for handling OpenAI API calls with MCP tools.

    Parameters
    ----------
    settings : Configurations
        language model configurations containing API keys and customisations
    langfuse_client : MonitoringClient
        client for monitoring and logging interactions, including Langfuse integration
    mcp_client : MCPClient
        client for managing MCP servers and their tools
    system_prompt : str | None, optional
        initial system prompt to set the context, by default None

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
        langfuse_client: MonitoringClient,
        mcp_client: MCPClient,
        system_prompt: str | None = None,
    ) -> None:
        self.settings = settings
        self.langfuse_client = langfuse_client
        self.mcp_client = mcp_client
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

    async def process_user_message(  # noqa: C901, PLR0912, PLR0915
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

        with self.langfuse_client.start_as_current_observation(
            name="generation counter 0", as_type="generation", input=user_message
        ) as generation_monitoring:
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

            generation_monitoring.update(output=assistant_message)

        counter = 1
        while finish_reason == "tool_calls":
            self.conversation_history.append(
                ChatCompletionAssistantMessageParam(
                    role="assistant", content=assistant_message, tool_calls=assistant_tool_calls
                )
            )

            LOGGER.debug(f"Identified tool calls: {assistant_tool_calls}.")

            for tool_call in assistant_tool_calls:
                with self.langfuse_client.start_as_current_observation(
                    name=f"tool call {tool_call['id']}", as_type="tool"
                ) as tool_monitoring:
                    tool_call_id = tool_call["id"]
                    tool_name = tool_call["function"]["name"]
                    tool_arguments = tool_call["function"]["arguments"]

                    try:
                        parsed_tool_arguments = json.loads(tool_arguments)
                    except json.JSONDecodeError as error:
                        self.conversation_history.append(
                            ChatCompletionToolMessageParam(
                                content=f"Error: {error}", role="tool", tool_call_id=tool_call_id
                            )
                        )
                    else:
                        tool_monitoring.update(input=parsed_tool_arguments)

                        tool_execution_result = await self.mcp_client.execute_tool_call(
                            tool_call_id, tool_name, parsed_tool_arguments
                        )

                        tool_call_events = self.mcp_client.tool_call_events[tool_call_id]

                        if not (elicitation_events := tool_call_events.get("elicitation_events")):
                            elicitation_information = (
                                f"No elicitation occurred for {tool_call_id=} to {tool_name=}."
                            )
                        else:
                            elicitation_information = (
                                f"Elicitation occurred for {tool_call_id=} to {tool_name=}."
                            )
                            for event_type, event_details in elicitation_events.items():
                                elicitation_information += f"\n{event_type}: {event_details}"

                        if not (sampling_events := tool_call_events.get("sampling_events")):
                            sampling_information = (
                                f"No sampling occurred for {tool_call_id=} to {tool_name=}."
                            )
                        else:
                            sampling_information = (
                                f"Sampling occurred for {tool_call_id=} to {tool_name=}."
                            )
                            for event_type, event_details in sampling_events.items():
                                sampling_information += f"\n{event_type}: {event_details}"

                        tool_monitoring.update(output=tool_execution_result)

                        self.conversation_history.append(
                            ChatCompletionToolMessageParam(
                                content=f"""Tool Execution Details

    {elicitation_information}

    {sampling_information}

    Tool Result

    {tool_execution_result}""",
                                role="tool",
                                tool_call_id=tool_call_id,
                            )
                        )

            with self.langfuse_client.start_as_current_observation(
                name=f"generation counter {counter}", as_type="generation"
            ) as generation_monitoring:
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

                generation_monitoring.update(output=assistant_message)

            counter += 1

        self.conversation_history.append({"role": "assistant", "content": assistant_message})


__all__ = ["OpenAIOrchestrator"]
