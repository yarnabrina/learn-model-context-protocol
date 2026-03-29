"""Configure logging."""

import logging
import logging.config
import logging.handlers
import typing

from pythonjsonlogger.json import JsonFormatter

from .configurations import Configurations, LogLevel


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


def create_structured_formatter() -> JsonFormatter:
    """Create a custom formatter for logging.

    Returns
    -------
    JsonFormatter
        formatter configured with JSON logging
    """
    return JsonFormatter(
        fmt="{asctime} {levelname} {name} {funcName} {lineno} {message}",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        style="{",
        validate=True,
        rename_fields={"asctime": "timestamp", "levelname": "level"},
        timestamp=False,
    )


def initiate_logging(settings: Configurations) -> None:
    """Initialize logging with JSON formatting.

    Parameters
    ----------
    settings : Configurations
        server configurations containing host, port, and other settings
    """
    logging_configurations = {
        "version": 1,
        "formatters": {
            "structured": {"()": create_structured_formatter},
            "unstructured": {
                "class": "logging.Formatter",
                "format": "{asctime} {levelname} {name} {funcName} {lineno} {message}",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                "style": "{",
            },
        },
        "filters": {"deactivate": {"()": DeactivateFilter}},
        "handlers": {
            "developer": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": LogLevel.DEBUG,
                "formatter": "unstructured",
                "filters": ["deactivate"] if not settings.debug else [],
                "filename": settings.log_file,
                "when": "midnight",
                "backupCount": 7,
                "encoding": "utf-8",
                "delay": True,
                "utc": True,
            },
            "user": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "structured",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {"py.warnings": {"handlers": ["developer", "user"], "level": "NOTSET"}},
        "root": {"handlers": ["developer", "user"], "level": "NOTSET"},
        "incremental": False,
        "disable_existing_loggers": False,
    }

    logging.config.dictConfig(logging_configurations)
    logging.captureWarnings(True)
