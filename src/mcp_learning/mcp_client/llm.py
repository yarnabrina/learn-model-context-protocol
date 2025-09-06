"""Provide interaction with OpenAI's API for chat completions."""

import collections.abc
import functools
import logging

import openai
import pydantic_settings
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolParam,
)

from .utils import (
    AzureOpenAIConfigurations,
    Configurations,
    HostedOpenAIConfigurations,
    LanguageModelProviderType,
    OpenAIConfigurations,
)

LOGGER = logging.getLogger(__name__)


class OpenAIClient:
    """Define client for OpenAI API interactions.

    Parameters
    ----------
    settings : Configurations
        language model configurations containing API keys and customisations

    Attributes
    ----------
    openai_client : openai.AsyncOpenAI
        OpenAI client instance configured based on the provided settings
    """

    def __init__(self: "OpenAIClient", settings: Configurations) -> None:
        self.settings = settings

    @functools.cached_property
    def openai_client(self: "OpenAIClient") -> openai.AsyncOpenAI:
        """Initialize the OpenAI client based on the provider type.

        Returns
        -------
        openai.AsyncOpenAI
            configured OpenAI client instance based on the provider type
        """
        language_model_provider: (
            AzureOpenAIConfigurations | HostedOpenAIConfigurations | OpenAIConfigurations
        ) = pydantic_settings.get_subcommand(self.settings)

        match language_model_provider.language_model_provider_type:
            case LanguageModelProviderType.AZURE_OPENAI:
                openai_client = openai.AsyncAzureOpenAI(
                    azure_endpoint=language_model_provider.azure_openai_endpoint,
                    azure_deployment=language_model_provider.azure_openai_deployment_name,
                    api_version=language_model_provider.azure_openai_api_version,
                    api_key=language_model_provider.azure_openai_api_key,
                )
            case LanguageModelProviderType.HOSTED_OPENAI:
                openai_client = openai.AsyncOpenAI(
                    api_key=language_model_provider.hosted_openai_api_key,
                    base_url=language_model_provider.hosted_openai_base_url,
                    default_headers=language_model_provider.hosted_openai_headers,
                )
            case LanguageModelProviderType.OPENAI:
                openai_client = openai.AsyncOpenAI(api_key=language_model_provider.openai_api_key)

        return openai_client

    def formulate_openai_inputs(
        self: "OpenAIClient",
        chat_history: list[ChatCompletionMessageParam],
        stream: bool,
        system_prompt: str | None = None,
        tools: list[ChatCompletionToolParam] | None = None,
        openai_customisations: dict | None = None,
    ) -> dict:
        """Construct the OpenAI API inputs based on the chat history and settings.

        Parameters
        ----------
        chat_history : list[ChatCompletionMessageParam]
            chat history to send to the OpenAI API
        stream : bool
            whether to stream the response or not
        system_prompt : str | None, optional
            initial system prompt to set the context, by default None
        tools : list[ChatCompletionToolParam] | None, optional
            available functions for OpenAI to call, by default None
        openai_customisations : dict | None, optional
            additional or non-default OpenAI parameters, by default None

        Returns
        -------
        dict
            OpenAI API inputs including messages, model, and other parameters
        """
        if system_prompt:
            chat_history = [
                ChatCompletionSystemMessageParam(content=system_prompt, role="system"),
                *chat_history,
            ]

        if openai_customisations is None:
            openai_customisations = {}

        openai_inputs = {
            "messages": chat_history,
            "model": self.settings.language_model,
            "max_completion_tokens": self.settings.language_model_max_tokens,
            "n": 1,
            "seed": 0,
            "store": False,
            "stream": stream,
            "temperature": self.settings.language_model_temperature,
            "top_p": self.settings.language_model_top_p,
            "timeout": self.settings.language_model_timeout,
            **openai_customisations,
        }

        if tools:
            openai_inputs.update(
                {"parallel_tool_calls": True, "tool_choice": "auto", "tools": tools}
            )

        LOGGER.debug(f"Formulated OpenAI inputs: {openai_inputs}")

        return openai_inputs

    async def get_non_streaming_openai_response(
        self: "OpenAIClient",
        chat_history: list[ChatCompletionMessageParam],
        system_prompt: str | None = None,
        tools: list[ChatCompletionToolParam] | None = None,
        openai_customisations: dict | None = None,
    ) -> ChatCompletion:
        """Get a non-streaming OpenAI response based on the chat history.

        Parameters
        ----------
        chat_history : list[ChatCompletionMessageParam]
            chat history to send to the OpenAI API
        system_prompt : str | None, optional
            initial system prompt to set the context, by default None
        tools : list[ChatCompletionToolParam] | None, optional
            available functions for OpenAI to call, by default None
        openai_customisations : dict | None, optional
            additional or non-default OpenAI parameters, by default None

        Returns
        -------
        ChatCompletion
            the OpenAI response object containing the model's reply
        """
        openai_inputs = self.formulate_openai_inputs(
            chat_history,
            False,
            system_prompt=system_prompt,
            tools=tools,
            openai_customisations=openai_customisations,
        )
        non_streaming_chat_completion = await self.openai_client.chat.completions.create(
            **openai_inputs
        )

        return non_streaming_chat_completion

    async def get_streaming_openai_response(
        self: "OpenAIClient",
        chat_history: list[ChatCompletionMessageParam],
        system_prompt: str | None = None,
        tools: list[ChatCompletionToolParam] | None = None,
        openai_customisations: dict | None = None,
    ) -> collections.abc.AsyncGenerator[ChatCompletionChunk]:
        """Get a streaming OpenAI response based on the chat history.

        Parameters
        ----------
        chat_history : list[ChatCompletionMessageParam]
            chat history to send to the OpenAI API
        system_prompt : str | None, optional
            initial system prompt to set the context, by default None
        tools : list[ChatCompletionToolParam] | None, optional
            available functions for OpenAI to call, by default None
        openai_customisations : dict | None, optional
            additional or non-default OpenAI parameters, by default None

        Yields
        ------
        Iterator[collections.abc.AsyncGenerator[ChatCompletionChunk]]
            streaming chunks of the OpenAI response as they are generated
        """
        openai_inputs = self.formulate_openai_inputs(
            chat_history,
            True,
            system_prompt=system_prompt,
            tools=tools,
            openai_customisations=openai_customisations,
        )
        streaming_chat_completion = await self.openai_client.chat.completions.create(
            **openai_inputs
        )

        async for chunk in streaming_chat_completion:
            yield chunk


__all__ = ["OpenAIClient"]
