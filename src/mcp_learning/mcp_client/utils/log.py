"""Configure logging."""

import logging
import logging.config
import typing

import rich.logging
import structlog

from .configurations import Configurations, LogLevel
from .console import CONSOLE


def create_rich_handler(level: int | str = logging.NOTSET) -> rich.logging.RichHandler:
    """Create a custom handler for logging.

    Parameters
    ----------
    level : int | str, optional
        logging level for the handler, by default logging.NOTSET

    Returns
    -------
    rich.logging.RichHandler
        handler configured with the specified level
    """
    return rich.logging.RichHandler(
        level=level, console=CONSOLE, show_time=False, show_level=True, show_path=False
    )


def create_foreign_pre_chain(include_callsite: bool = False) -> list:
    """Create structlog processors for non-structlog log records.

    Parameters
    ----------
    include_callsite : bool, optional
        whether to include filename/function/line metadata, by default False

    Returns
    -------
    list
        processor chain for foreign stdlib log records
    """
    foreign_pre_chain = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if include_callsite:
        foreign_pre_chain.append(
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            )
        )

    return foreign_pre_chain


def create_structured_formatter() -> structlog.stdlib.ProcessorFormatter:
    """Create a structured formatter for developer logs.

    Returns
    -------
    structlog.stdlib.ProcessorFormatter
        JSON formatter for file-based developer logs
    """
    return structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=create_foreign_pre_chain(include_callsite=True),
    )


def create_human_formatter() -> structlog.stdlib.ProcessorFormatter:
    """Create a human-friendly formatter for user-facing stream logs.

    Returns
    -------
    structlog.stdlib.ProcessorFormatter
        rich console formatter for user-facing logs
    """
    return structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(), foreign_pre_chain=create_foreign_pre_chain()
    )


class DeactivateFilter(logging.Filter):
    """Define filter to disable logging handlers."""

    def filter(self: typing.Self, record: logging.LogRecord) -> typing.Literal[False]:
        """Disable records.

        Parameters
        ----------
        record : logging.LogRecord
            the log record to filter

        Returns
        -------
        typing.Literal[False]
            disablity status of the record
        """
        del record

        return False


class SuppressTracebackFilter(logging.Filter):
    """Define filter to suppress traceback in logs."""

    def filter(self: typing.Self, record: logging.LogRecord) -> logging.LogRecord:
        """Remove traceback from log records.

        Parameters
        ----------
        record : logging.LogRecord
            the log record to filter

        Returns
        -------
        logging.LogRecord
            updated log record without traceback
        """
        duplicate_record = logging.makeLogRecord(record.__dict__)

        duplicate_record.exc_info = None
        duplicate_record.exc_text = None

        return duplicate_record


def initiate_logging(settings: Configurations) -> None:
    """Initialize logging with structured and human-friendly formatting.

    Parameters
    ----------
    settings : Configurations
        language model configurations containing API keys and customisations
    """
    logging_configurations = {
        "version": 1,
        "formatters": {
            "detailed": {"()": create_structured_formatter},
            "simple": {"()": create_human_formatter},
        },
        "filters": {
            "deactivate": {"()": DeactivateFilter},
            "suppress": {"()": SuppressTracebackFilter},
        },
        "handlers": {
            "developer": {
                "class": "logging.FileHandler",
                "level": settings.log_level,
                "formatter": "detailed",
                "filters": ["deactivate"] if not settings.debug else [],
                "filename": settings.log_file,
                "mode": "a",
                "encoding": "utf-8",
                "delay": True,
            },
            "user": {
                "()": create_rich_handler,
                "level": LogLevel.WARNING,
                "formatter": "simple",
                "filters": ["suppress"],
            },
        },
        "loggers": {"py.warnings": {"handlers": ["developer", "user"], "level": "NOTSET"}},
        "root": {"handlers": ["developer", "user"], "level": "NOTSET"},
        "incremental": False,
        "disable_existing_loggers": False,
    }

    logging.config.dictConfig(logging_configurations)
    logging.captureWarnings(True)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
