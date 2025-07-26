"""Provide console formatting utilities for user interaction."""

import typing

import rich

CONSOLE = rich.get_console()


def user_prompt() -> str:
    """Prompt the user for input with a custom format.

    Returns
    -------
    str
        user provided input
    """
    return CONSOLE.input(prompt="[bold blue][You][/bold blue] ")


def bot_response(message: typing.Any) -> None:  # noqa: ANN401
    """Print the bot's response in a formatted way.

    Parameters
    ----------
    message : typing.Any
        message to print
    """
    CONSOLE.print(f"[bold magenta][INFO][/bold magenta] {message}")


def llm_response(message: typing.Any, start: bool = False) -> None:  # noqa: ANN401
    """Print the LLM response in a formatted way.

    Parameters
    ----------
    message : typing.Any
        message to print
    start : bool, optional
        indicator of start of a new response, by default False
    """
    if start:
        CONSOLE.print("[bold green][Bot][/bold green] ", end="")

    CONSOLE.print(message, end="")


def internal_info(message: typing.Any) -> None:  # noqa: ANN401
    """Print internal debug information in a formatted way.

    Parameters
    ----------
    message : typing.Any
        message to print
    """
    CONSOLE.print(f"[bold cyan][DEBUG][/bold cyan] {message}", end="")
