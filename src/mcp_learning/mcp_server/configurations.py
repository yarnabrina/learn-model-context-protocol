"""Define configurations for the MCP server."""

import enum

import pydantic_settings

ENVIRONMENT_FILE = "mcp_server.env"
ENVIRONMENT_FILE_ENCODING = "utf-8"


class LogLevel(enum.StrEnum):
    """Define log levels for the server."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServerConfigurations(pydantic_settings.BaseSettings):
    """Define configurations for the MCP server."""

    debug: pydantic_settings.CliImplicitFlag[bool] = False
    log_level: LogLevel = LogLevel.WARNING


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
        cli_parse_args=True, env_file=ENVIRONMENT_FILE, env_file_encoding=ENVIRONMENT_FILE_ENCODING
    )


__all__ = [
    "ENVIRONMENT_FILE",
    "ENVIRONMENT_FILE_ENCODING",
    "Configurations",
    "HttpConfigurations",
    "LogLevel",
    "ServerConfigurations",
    "StreamableHttpConfigurations",
]
