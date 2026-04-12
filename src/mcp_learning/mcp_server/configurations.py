"""Define configurations for the MCP server."""

import pydantic_settings

from ..logging_bootstrap import LogLevel, RuntimeEnvironment

SETTINGS_FILE = "mcp_server.env"
SETTINGS_FILE_ENCODING = "utf-8"


class ServerConfigurations(pydantic_settings.BaseSettings):
    """Define configurations for the MCP server."""

    debug: pydantic_settings.CliImplicitFlag[bool] = False
    runtime_environment: RuntimeEnvironment = RuntimeEnvironment.LOCAL
    log_level: LogLevel | None = None
    log_file: str | None = None


class HttpConfigurations(pydantic_settings.BaseSettings):
    """Define HTTP configurations for the MCP server."""

    host: str = "127.0.0.1"
    port: int = 8000


class StreamableHttpConfigurations(pydantic_settings.BaseSettings):
    """Define streamable HTTP configurations for the MCP server."""

    streamable_http_path: str = "/mcp"
    json_response: pydantic_settings.CliImplicitFlag[bool] = False
    stateless_http: pydantic_settings.CliImplicitFlag[bool] = False


class Configurations(ServerConfigurations, HttpConfigurations, StreamableHttpConfigurations):
    """Aggregate all configurations for the MCP server."""

    model_config = pydantic_settings.SettingsConfigDict(
        cli_parse_args=True, env_file=SETTINGS_FILE, env_file_encoding=SETTINGS_FILE_ENCODING
    )


__all__ = [
    "SETTINGS_FILE",
    "SETTINGS_FILE_ENCODING",
    "Configurations",
    "HttpConfigurations",
    "LogLevel",
    "RuntimeEnvironment",
    "ServerConfigurations",
    "StreamableHttpConfigurations",
]
