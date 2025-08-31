"""Provide console formatting utilities for user interaction."""

import logging
import logging.config
import typing

import rich
import rich.logging
import rich.pretty

from .configurations import Configurations
from .utils import MissingOptionalDependencyError, validate_optional_dependency_installation

CONSOLE = rich.get_console()

try:
    validate_optional_dependency_installation("prompt-toolkit", import_name="prompt_toolkit")
except MissingOptionalDependencyError:
    ENHANCED_CLI_AVAILABLE = False
else:
    ENHANCED_CLI_AVAILABLE = True

    import prompt_toolkit
    import prompt_toolkit.key_binding
    import prompt_toolkit.styles

    SESSION = prompt_toolkit.PromptSession()


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


async def user_prompt() -> str:
    """Prompt the user for input with a custom format.

    Returns
    -------
    str
        user provided input
    """
    if not ENHANCED_CLI_AVAILABLE:
        return CONSOLE.input(prompt="\n[bold blue][You][/bold blue] ")

    key_bindings = prompt_toolkit.key_binding.KeyBindings()

    @key_bindings.add("enter")
    def submit_input(event: prompt_toolkit.key_binding.KeyPressEvent) -> None:
        """Submit the input on Enter key press.

        Parameters
        ----------
        event : prompt_toolkit.key_binding.KeyPressEvent
            key press event
        """
        buffer = event.current_buffer

        if (
            event.current_buffer.document.is_cursor_at_the_end
            or event.current_buffer.document.is_cursor_at_the_end_of_line
        ):
            buffer.validate_and_handle()
        else:
            buffer.insert_text("\n")

    style = prompt_toolkit.styles.Style.from_dict({"prompt": "bold blue"})

    prompt = await SESSION.prompt_async(
        [("class:prompt", "\n[You] ")], key_bindings=key_bindings, style=style, multiline=True
    )

    return prompt


def bot_response(message: typing.Any) -> None:  # noqa: ANN401
    """Print the bot's response in a formatted way.

    Parameters
    ----------
    message : typing.Any
        message to print
    """
    if not isinstance(message, str):
        message = rich.pretty.Pretty(message)

    CONSOLE.print("[bold magenta][Bot][/bold magenta]", message)


async def llm_response(token_stream: typing.AsyncIterable[str]) -> None:
    """Print the LLM response in a formatted way.

    Parameters
    ----------
    token_stream : typing.AsyncIterable[str]
        stream of message to print
    """
    CONSOLE.print("[bold green][LLM][/bold green] ", end="")

    async for token in token_stream:
        CONSOLE.print(token, end="")
