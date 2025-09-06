"""Configure logging."""

import logging
import logging.config
import typing

import rich.logging

from .configurations import Configurations
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


class DeactivateFilter(logging.Filter):
    """Define filter to disable logging handlers."""

    def filter(self: "DeactivateFilter", record: logging.LogRecord) -> typing.Literal[False]:
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

    def filter(self: "SuppressTracebackFilter", record: logging.LogRecord) -> logging.LogRecord:
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
        record.exc_info = None
        record.exc_text = None

        return record


def initiate_logging(settings: Configurations) -> None:
    """Initialize logging with rich formatting.

    Parameters
    ----------
    settings : Configurations
        language model configurations containing API keys and customisations
    """
    logging_configurations = {
        "version": 1,
        "formatters": {
            "detailed": {
                "class": "logging.Formatter",
                "format": "{asctime} {levelname} {name} {funcName} {lineno} {message}",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
                "style": "{",
                "validate": True,
            },
            "simple": {
                "class": "logging.Formatter",
                "format": "{message}",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
                "style": "{",
                "validate": True,
            },
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
                "level": settings.log_level,
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
