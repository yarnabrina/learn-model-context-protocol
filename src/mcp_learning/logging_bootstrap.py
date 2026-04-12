"""Bootstrap stdlib-backed structlog logging."""

import dataclasses
import datetime
import enum
import logging
import logging.config
import re
import warnings

import structlog


class LoggingComponent(enum.StrEnum):
    """Define supported logging components."""

    MCP_SERVER = "mcp_server"
    MCP_CLIENT = "mcp_client"


class RuntimeEnvironment(enum.StrEnum):
    """Define supported runtime environments."""

    LOCAL = "local"
    PRODUCTION = "production"


class LogLevel(enum.StrEnum):
    """Define stdlib-compatible log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormatter(enum.StrEnum):
    """Define supported formatter styles for handlers."""

    UNSTRUCTURED = "unstructured"
    STRUCTURED = "structured"


class LogHandler(enum.StrEnum):
    """Define supported handler names for dictConfig wiring."""

    NULL = "null"
    STREAM = "stream"
    FILE = "file"


@dataclasses.dataclass(slots=True, kw_only=True)
class LoggingBootstrapSettings:
    """Define shared logging bootstrap inputs.

    Attributes
    ----------
    component : LoggingComponent
        component whose policy row controls handlers, formatters, and defaults
    debug : bool
        enables debug policy row; debug mode enforces DEBUG levels from policy
    runtime_environment : RuntimeEnvironment, optional
        deployment mode used for conflict handling (warn in local, fail in production),
        by default RuntimeEnvironment.LOCAL
    log_level : LogLevel | None
        optional override level applied only to handlers activated by non-debug policy,
        by default None
    log_file : str | None, optional
        optional file path override used only when file handler is policy-enabled,
        by default None
    """

    component: LoggingComponent
    debug: bool
    runtime_environment: RuntimeEnvironment = RuntimeEnvironment.LOCAL
    log_level: LogLevel | None = None
    log_file: str | None = None
    redaction_enabled: bool = True


PATTERN_REDACTION_FIELDS = ("event", "message")

REDACTION_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._=-]{8,}", re.IGNORECASE)


def redact_text(value: str) -> str:
    """Apply minimal regex-based redaction to a string value.

    Parameters
    ----------
    value : str
        string to redact

    Returns
    -------
    str
        string with matched patterns replaced by <REDACTED>
    """
    return REDACTION_PATTERN.sub("<REDACTED>", value)


def redact_value(value: object) -> object:
    """Recursively apply pattern-based redaction to common container value types.

    Parameters
    ----------
    value : object
        value to redact

    Returns
    -------
    object
        redacted equivalent of the input value

    Notes
    -----
    Strings are scanned for patterns.
    Dicts, lists, and tuples are traversed recursively.
    All other types are returned unchanged.
    """
    if isinstance(value, str):
        return redact_text(value)

    if isinstance(value, tuple):
        return tuple(redact_value(inner_value) for inner_value in value)

    if isinstance(value, list):
        return [redact_value(inner_value) for inner_value in value]

    if isinstance(value, dict):
        return {key: redact_value(inner_value) for key, inner_value in value.items()}

    return value


def sanitize_event_dict(
    event_dict: structlog.typing.EventDict,
    redaction_enabled: bool,
    runtime_environment: RuntimeEnvironment,
    component: LoggingComponent,
) -> structlog.typing.EventDict:
    """Sanitize selected client log fields using minimal redaction rules.

    Parameters
    ----------
    event_dict : structlog.typing.EventDict
        mutable structlog event dictionary to sanitize in place
    redaction_enabled : bool
        whether redaction is active; ignored and treated as True in production
    runtime_environment : RuntimeEnvironment
        current runtime environment; forces redaction on in production
    component : LoggingComponent
        component identity; sanitization is skipped unless MCP_CLIENT

    Returns
    -------
    structlog.typing.EventDict
        sanitized event dictionary

    Notes
    -----
    Pattern redaction is only applied to selected content fields.
    Generic metadata fields are left unchanged.
    """
    if component != LoggingComponent.MCP_CLIENT:
        return event_dict

    if runtime_environment == RuntimeEnvironment.PRODUCTION:
        effective_redaction_enabled = True
    else:
        effective_redaction_enabled = redaction_enabled

    if not effective_redaction_enabled:
        return event_dict

    for key, value in list(event_dict.items()):
        if key.lower() in PATTERN_REDACTION_FIELDS:
            event_dict[key] = redact_value(value)

    return event_dict


def get_dated_log_file(component: LoggingComponent) -> str:
    """Create a dated default log file path for a component.

    Parameters
    ----------
    component : LoggingComponent
        runtime component name

    Returns
    -------
    str
        default dated log file path
    """
    today = datetime.datetime.now(tz=datetime.UTC).date().isoformat()

    return f"{component.value}_{today}.log"


@dataclasses.dataclass(slots=True, kw_only=True)
class LoggingPolicy:
    """Define resolved logging policy for a runtime mode."""

    stream_formatter: LogFormatter | None
    stream_level: LogLevel | None
    file_formatter: LogFormatter | None
    file_level: LogLevel | None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PolicyKey:
    """Define lookup key for policy matrix rows."""

    component: LoggingComponent
    runtime_environment: RuntimeEnvironment
    debug: bool


POLICY_MATRIX: dict[PolicyKey, LoggingPolicy] = {
    PolicyKey(
        component=LoggingComponent.MCP_SERVER,
        runtime_environment=RuntimeEnvironment.LOCAL,
        debug=False,
    ): LoggingPolicy(
        stream_formatter=LogFormatter.UNSTRUCTURED,
        stream_level=LogLevel.INFO,
        file_formatter=None,
        file_level=None,
    ),
    PolicyKey(
        component=LoggingComponent.MCP_SERVER,
        runtime_environment=RuntimeEnvironment.LOCAL,
        debug=True,
    ): LoggingPolicy(
        stream_formatter=LogFormatter.UNSTRUCTURED,
        stream_level=LogLevel.DEBUG,
        file_formatter=LogFormatter.STRUCTURED,
        file_level=LogLevel.DEBUG,
    ),
    PolicyKey(
        component=LoggingComponent.MCP_SERVER,
        runtime_environment=RuntimeEnvironment.PRODUCTION,
        debug=False,
    ): LoggingPolicy(
        stream_formatter=LogFormatter.STRUCTURED,
        stream_level=LogLevel.INFO,
        file_formatter=None,
        file_level=None,
    ),
    PolicyKey(
        component=LoggingComponent.MCP_SERVER,
        runtime_environment=RuntimeEnvironment.PRODUCTION,
        debug=True,
    ): LoggingPolicy(
        stream_formatter=LogFormatter.STRUCTURED,
        stream_level=LogLevel.DEBUG,
        file_formatter=None,
        file_level=None,
    ),
    PolicyKey(
        component=LoggingComponent.MCP_CLIENT,
        runtime_environment=RuntimeEnvironment.LOCAL,
        debug=False,
    ): LoggingPolicy(
        stream_formatter=None, stream_level=None, file_formatter=None, file_level=None
    ),
    PolicyKey(
        component=LoggingComponent.MCP_CLIENT,
        runtime_environment=RuntimeEnvironment.LOCAL,
        debug=True,
    ): LoggingPolicy(
        stream_formatter=LogFormatter.UNSTRUCTURED,
        stream_level=LogLevel.DEBUG,
        file_formatter=LogFormatter.STRUCTURED,
        file_level=LogLevel.DEBUG,
    ),
    PolicyKey(
        component=LoggingComponent.MCP_CLIENT,
        runtime_environment=RuntimeEnvironment.PRODUCTION,
        debug=False,
    ): LoggingPolicy(
        stream_formatter=None, stream_level=None, file_formatter=None, file_level=None
    ),
    PolicyKey(
        component=LoggingComponent.MCP_CLIENT,
        runtime_environment=RuntimeEnvironment.PRODUCTION,
        debug=True,
    ): LoggingPolicy(
        stream_formatter=None, stream_level=None, file_formatter=None, file_level=None
    ),
}


def resolve_fastmcp_log_level(settings: LoggingBootstrapSettings) -> str:
    """Resolve FastMCP log level from bootstrap inputs.

    Parameters
    ----------
    settings : LoggingBootstrapSettings
        shared logging bootstrap inputs

    Returns
    -------
    str
        FastMCP-compatible log level
    """
    if settings.debug:
        return LogLevel.DEBUG

    if settings.log_level is None:
        return LogLevel.INFO

    return settings.log_level


def handle_policy_conflict(settings: LoggingBootstrapSettings, message: str) -> None:
    """Handle policy conflicts according to runtime environment.

    Parameters
    ----------
    settings : LoggingBootstrapSettings
        shared logging bootstrap inputs
    message : str
        conflict message

    Raises
    ------
    ValueError
        if runtime environment is production
    """
    if settings.runtime_environment == RuntimeEnvironment.PRODUCTION:
        raise ValueError(message)

    warnings.warn(message, UserWarning, stacklevel=4)


def resolve_effective_levels(
    settings: LoggingBootstrapSettings, policy: LoggingPolicy
) -> tuple[LogLevel | None, LogLevel | None]:
    """Resolve effective stream and file levels under mode-specific rules.

    Parameters
    ----------
    settings : LoggingBootstrapSettings
        shared logging bootstrap inputs
    policy : LoggingPolicy
        resolved runtime policy

    Returns
    -------
    tuple[LogLevel | None, LogLevel | None]
        effective stream and file handler levels
    """
    stream_level = policy.stream_level
    file_level = policy.file_level

    if settings.debug:
        if settings.log_level is not None and settings.log_level != LogLevel.DEBUG:
            handle_policy_conflict(
                settings,
                f"Debug mode ignores conflicting log_level and enforces {LogLevel.DEBUG}.",
            )

        return stream_level, file_level

    if settings.log_level is None:
        return stream_level, file_level

    if stream_level is None and file_level is None:
        handle_policy_conflict(
            settings,
            "Log level override ignored because policy activates no handlers in this mode.",
        )
        return stream_level, file_level

    return (
        settings.log_level if stream_level is not None else None,
        settings.log_level if file_level is not None else None,
    )


def resolve_effective_file_path(
    settings: LoggingBootstrapSettings, policy: LoggingPolicy
) -> str | None:
    """Resolve file path when file logging is policy-enabled.

    Parameters
    ----------
    settings : LoggingBootstrapSettings
        shared logging bootstrap inputs
    policy : LoggingPolicy
        resolved runtime policy

    Returns
    -------
    str | None
        effective file path if file handler is active
    """
    if policy.file_formatter is None or policy.file_level is None:
        if settings.log_file is not None:
            handle_policy_conflict(
                settings,
                "Log file override ignored because file logging is disabled in this mode.",
            )
        return None

    return settings.log_file or get_dated_log_file(settings.component)


def initiate_logging(settings: LoggingBootstrapSettings) -> None:
    """Initialize minimal stdlib-backed structlog logging.

    Parameters
    ----------
    settings : LoggingBootstrapSettings
        shared logging bootstrap inputs
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    def inject_base_fields(
        _: structlog.typing.WrappedLogger, __: str, event_dict: structlog.typing.EventDict
    ) -> structlog.typing.EventDict:
        """Inject canonical base fields into the event dictionary.

        Parameters
        ----------
        _ : structlog.typing.WrappedLogger
            bound logger instance (unused)
        __ : str
            method name (unused)
        event_dict : structlog.typing.EventDict
            mutable event dictionary being processed

        Returns
        -------
        structlog.typing.EventDict
            event dictionary with base fields injected where absent
        """
        if "event" in event_dict and "message" not in event_dict:
            event_dict["message"] = event_dict["event"]

        if "level" in event_dict and "log.level" not in event_dict:
            event_dict["log.level"] = event_dict["level"]

        if "logger" in event_dict and "logger.name" not in event_dict:
            event_dict["logger.name"] = event_dict["logger"]

        event_dict.setdefault("event.group", "logging")
        event_dict.setdefault("event.type", "record")
        event_dict.setdefault("event.action", "emit")
        event_dict.setdefault("event.status", "succeeded")
        event_dict.setdefault("service.name", settings.component)
        event_dict.setdefault("deployment.environment", settings.runtime_environment)
        event_dict.setdefault("debug.enabled", settings.debug)
        event_dict.setdefault("schema.version", "1.0")

        return event_dict

    def sanitize_fields(
        _: structlog.typing.WrappedLogger, __: str, event_dict: structlog.typing.EventDict
    ) -> structlog.typing.EventDict:
        """Apply minimal client-only redaction before rendering.

        Parameters
        ----------
        _ : structlog.typing.WrappedLogger
            bound logger instance (unused)
        __ : str
            method name (unused)
        event_dict : structlog.typing.EventDict
            mutable event dictionary being processed

        Returns
        -------
        structlog.typing.EventDict
            sanitized event dictionary
        """
        return sanitize_event_dict(
            event_dict,
            settings.redaction_enabled,
            settings.runtime_environment,
            settings.component,
        )

    foreign_pre_chain = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        timestamper,
        structlog.processors.format_exc_info,
        inject_base_fields,
        sanitize_fields,
    ]

    policy_key = PolicyKey(
        component=settings.component,
        runtime_environment=settings.runtime_environment,
        debug=settings.debug,
    )
    policy = POLICY_MATRIX[policy_key]
    stream_level, file_level = resolve_effective_levels(settings, policy)
    file_path = resolve_effective_file_path(settings, policy)

    handlers: dict[str, dict[str, object]] = {
        LogHandler.NULL: {"class": "logging.NullHandler", "level": "NOTSET"}
    }
    root_handlers: list[str]

    if policy.stream_formatter is not None and stream_level is not None:
        handlers[LogHandler.STREAM] = {
            "class": "logging.StreamHandler",
            "level": stream_level,
            "formatter": policy.stream_formatter,
            "stream": "ext://sys.stderr",
        }
        root_handlers = [LogHandler.STREAM]
    else:
        root_handlers = [LogHandler.NULL]

    if policy.file_formatter is not None and file_level is not None and file_path is not None:
        handlers[LogHandler.FILE] = {
            "class": "logging.FileHandler",
            "level": file_level,
            "formatter": policy.file_formatter,
            "filename": file_path,
            "mode": "a",
            "encoding": "utf-8",
            "delay": True,
        }
        root_handlers.append(LogHandler.FILE)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                LogFormatter.UNSTRUCTURED: {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.dev.ConsoleRenderer(colors=True, event_key="message"),
                    "foreign_pre_chain": foreign_pre_chain,
                },
                LogFormatter.STRUCTURED: {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.processors.JSONRenderer(sort_keys=False),
                    "foreign_pre_chain": foreign_pre_chain,
                },
            },
            "handlers": handlers,
            "root": {"handlers": root_handlers, "level": "NOTSET"},
            "loggers": {"py.warnings": {"handlers": root_handlers, "level": "NOTSET"}},
        }
    )
    logging.captureWarnings(True)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.ExtraAdder(),
            timestamper,
            structlog.processors.format_exc_info,
            inject_base_fields,
            sanitize_fields,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


__all__ = [
    "LogLevel",
    "LoggingBootstrapSettings",
    "LoggingComponent",
    "RuntimeEnvironment",
    "get_dated_log_file",
    "initiate_logging",
    "redact_text",
    "redact_value",
    "resolve_fastmcp_log_level",
    "sanitize_event_dict",
]
