"""Bootstrap stdlib-backed structlog logging."""

import dataclasses
import enum
import logging
import logging.config

import structlog


class LoggingComponent(enum.StrEnum):
    """Define supported logging components."""

    MCP_SERVER = "mcp_server"
    MCP_CLIENT = "mcp_client"


class LoggingEnvironment(enum.StrEnum):
    """Define supported logging environments."""

    LOCAL = "local"
    PRODUCTION = "production"


@dataclasses.dataclass(slots=True, kw_only=True)
class LoggingBootstrapSettings:
    """Define shared logging bootstrap inputs.

    Parameters
    ----------
    component : LoggingComponent
        runtime component name
    debug : bool
        debug mode flag
    log_level : str | int
        stdlib-compatible logging level
    environment : LoggingEnvironment
        runtime environment, reserved for later policy expansion
    log_file : str | None
        optional log file path, reserved for later policy expansion
    service_version : str | None
        optional service version, reserved for later schema enrichment
    """

    component: LoggingComponent
    debug: bool
    log_level: str | int
    environment: LoggingEnvironment = LoggingEnvironment.LOCAL
    log_file: str | None = None
    service_version: str | None = None


def initiate_logging(settings: LoggingBootstrapSettings) -> None:
    """Initialize minimal stdlib-backed structlog logging.

    Parameters
    ----------
    settings : LoggingBootstrapSettings
        shared logging bootstrap inputs
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    foreign_pre_chain = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
        structlog.processors.format_exc_info,
    ]

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.dev.ConsoleRenderer(colors=True),
                    "foreign_pre_chain": foreign_pre_chain,
                }
            },
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "level": settings.log_level,
                    "formatter": "console",
                    "stream": "ext://sys.stderr",
                }
            },
            "root": {"handlers": ["stderr"], "level": settings.log_level},
            "loggers": {"py.warnings": {"handlers": ["stderr"], "level": settings.log_level}},
        }
    )
    logging.captureWarnings(True)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
