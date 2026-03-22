"""Provide utility functions."""

import typing

import rich
import rich.pretty

from .dependencies import MissingOptionalDependencyError, validate_optional_dependency_installation

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


async def llm_response(token_stream: typing.AsyncIterable[str]) -> str:
    """Print the LLM response in a formatted way.

    Parameters
    ----------
    token_stream : typing.AsyncIterable[str]
        stream of message to print

    Returns
    -------
    str
        full response as a single string
    """
    CONSOLE.print("[bold green][LLM][/bold green] ", end="")

    full_response = ""
    async for token in token_stream:
        CONSOLE.print(token, end="")

        full_response += token

    return full_response


def trace_tool_input(tool_name: str, input_data: dict) -> None:
    """Print the MCP tool input in a formatted way.

    Parameters
    ----------
    tool_name : str
        name of the MCP tool being called
    input_data : dict | None, optional
        input parameters provided to the tool, by default None
    """
    CONSOLE.print(f"[bold yellow][Tool Input][/bold yellow] {tool_name}: {input_data}")


def trace_tool_output(tool_name: str, output_data: dict) -> None:
    """Print the MCP tool output in a formatted way.

    Parameters
    ----------
    tool_name : str
        name of the MCP tool being called
    output_data : dict | None, optional
        output results returned by the tool, by default None
    """
    CONSOLE.print(f"[bold yellow][Tool Output][/bold yellow] {tool_name}: {output_data}")


__all__ = [
    "CONSOLE",
    "ENHANCED_CLI_AVAILABLE",
    "SESSION",
    "bot_response",
    "llm_response",
    "trace_tool_input",
    "trace_tool_output",
    "user_prompt",
]
