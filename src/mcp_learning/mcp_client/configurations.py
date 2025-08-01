"""Define configurations for the MCP client."""

import enum
import typing

import pydantic
import pydantic_settings

ENVIRONMENT_FILE = "mcp_client.env"
ENVIRONMENT_FILE_ENCODING = "utf-8"


class LanguageModelProviderType(enum.StrEnum):
    """Define types of language model providers."""

    AZURE_OPENAI = "azure_openai"
    HOSTED_OPENAI = "hosted_openai"
    OPENAI = "openai"


class AzureOpenAIConfigurations(pydantic_settings.BaseSettings):
    """Define configurations for Azure OpenAI."""

    language_model_provider_type: typing.Literal[LanguageModelProviderType.AZURE_OPENAI] = (
        LanguageModelProviderType.AZURE_OPENAI
    )
    azure_openai_endpoint: str
    azure_openai_deployment_name: str
    azure_openai_api_version: str
    azure_openai_api_key: str


class HostedOpenAIConfigurations(pydantic_settings.BaseSettings):
    """Define configurations for Hosted OpenAI."""

    language_model_provider_type: typing.Literal[LanguageModelProviderType.HOSTED_OPENAI] = (
        LanguageModelProviderType.HOSTED_OPENAI
    )
    hosted_openai_api_key: str
    hosted_openai_base_url: str
    hosted_openai_headers: dict | None = None

    @pydantic.model_validator(mode="after")
    def validate(self: "HostedOpenAIConfigurations") -> "HostedOpenAIConfigurations":
        """Validate that the provided URL is valid.

        Raises
        ------
        ValueError
            if the provided URL is invalid

        Returns
        -------
        HostedOpenAIConfigurations
            validated configurations
        """
        try:
            pydantic.HttpUrl(self.hosted_openai_base_url)
        except pydantic.ValidationError as error:
            raise ValueError from error

        return self


class OpenAIConfigurations(pydantic_settings.BaseSettings):
    """Define configurations for OpenAI."""

    language_model_provider_type: typing.Literal[LanguageModelProviderType.OPENAI] = (
        LanguageModelProviderType.OPENAI
    )
    openai_api_key: str


class LanguageModelProviderConfigurations(pydantic_settings.BaseSettings):
    """Define configurations for language model providers."""

    azure_openai_provider: pydantic_settings.CliSubCommand[AzureOpenAIConfigurations] = (
        pydantic.Field(alias=LanguageModelProviderType.AZURE_OPENAI)
    )
    hosted_openai_provider: pydantic_settings.CliSubCommand[HostedOpenAIConfigurations] = (
        pydantic.Field(alias=LanguageModelProviderType.HOSTED_OPENAI)
    )
    openai_provider: pydantic_settings.CliSubCommand[OpenAIConfigurations] = pydantic.Field(
        alias=LanguageModelProviderType.OPENAI
    )


class LanguageModelConfigurations(pydantic_settings.BaseSettings):
    """Define configurations for language models."""

    language_model: str = "gpt-4o-mini"
    language_model_max_tokens: int = 4096
    language_model_temperature: float = 0.1
    language_model_top_p: float = 0.9
    language_model_timeout: int = 300


class Configurations(LanguageModelConfigurations, LanguageModelProviderConfigurations):
    """Aggregate all configurations for the MCP client."""

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=ENVIRONMENT_FILE,
        env_file_encoding=ENVIRONMENT_FILE_ENCODING,
        cli_parse_args=True,
        cli_ignore_unknown_args=True,
    )


__all__ = [
    "ENVIRONMENT_FILE",
    "ENVIRONMENT_FILE_ENCODING",
    "AzureOpenAIConfigurations",
    "Configurations",
    "HostedOpenAIConfigurations",
    "LanguageModelConfigurations",
    "LanguageModelProviderConfigurations",
    "LanguageModelProviderType",
    "OpenAIConfigurations",
]
