"""Initialise the chat interface for the MCP client."""

import asyncio
import enum
import functools
import json
import re
import sys

from .client import MCPClient, Status
from .orchestrator import OpenAIOrchestrator
from .utils import (
    Configurations,
    bot_response,
    get_monitoring_client,
    initiate_logging,
    llm_response,
    user_prompt,
)

HELP_MESSAGE = """
/help
    Displays this help message.

/add_server <server_name> <server_url> [<headers_json>]
    Adds or registers a new MCP server.

/remove_server <server_name>
    Removes an existing MCP server.

/list_servers
    Lists all configured MCP servers.

/list_tools <server_name>
    Lists available tools for a specific server.

/describe_tool <server_name> <tool_name>
    Displays details for a specific tool on a server.

/quit
    Exits the chat.
"""

SYSTEM_PROMPT = f"""You are a helpful assistant created to demonstrate the use of available tools.

Your primary objective is to showcase the functionality of the provided tools. Whenever a user's request can be addressed by a tool, you **must** use it, even if the task appears simple. This is essential for demonstration purposes.

If a tool call fails or produces an incorrect result, clearly inform the user of the error. After reporting the issue, you may provide the correct answer yourself, if possible, to highlight the difference.

If a tool call requests sampling, and it happens correctly, you should first mention the sampling request and result, and then report the tool call result.

If a tool call requests elicitation, and if the user provides a correction, you should report the tool call result with the elicitation information included.

Always **prioritise using tools** for appropriate tasks and be transparent about any limitations or errors.

If a user's message contains typographical errors or appears misdirected, do your best to interpret their intent and suggest the correct command.

The available commands are:

{HELP_MESSAGE}
"""  # noqa: E501


class ChatCommand(enum.StrEnum):
    """Define commands for the chat interface."""

    HELP = "help"
    ADD_SERVER = "add_server"
    REMOVE_SERVER = "remove_server"
    LIST_SERVERS = "list_servers"
    LIST_TOOLS = "list_tools"
    DESCRIBE_TOOL = "describe_tool"
    QUIT = "quit"


class ChatInterface:
    """Define the chat interface for interacting with the MCP client.

    Parameters
    ----------
    settings : Configurations
        language model configurations containing API keys and customisations

    Attributes
    ----------
    langfuse_client : langfuse.Langfuse | NoOpLangfuseClient
        client for tracking interactions and events
    mcp_client : MCPClient
        client for managing MCP servers and their tools
    llm_orchestrator : OpenAIOrchestrator
        orchestrator instance for handling language model interactions
    """

    def __init__(self: "ChatInterface", settings: Configurations) -> None:
        self.settings = settings

        self.langfuse_client = get_monitoring_client(settings)
        self.mcp_client = MCPClient(settings, self.langfuse_client)
        self.llm_orchestrator = OpenAIOrchestrator(
            self.settings,
            self.langfuse_client,
            system_prompt=SYSTEM_PROMPT,
            mcp_client=self.mcp_client,
        )

    @functools.cached_property
    def command_patterns(self: "ChatInterface") -> dict[ChatCommand, str]:
        """Define regex patterns for chat commands.

        Returns
        -------
        dict[ChatCommand, str]
            mapping of chat commands to their regex patterns
        """
        return {
            ChatCommand.HELP: r"^/help$",
            ChatCommand.ADD_SERVER: r"^/add_server\s+(?P<server_name>\S+)\s+(?P<server_url>\S+)(?:\s+(?P<server_headers>\{.*\}))?$",  # noqa: E501, pylint: disable=line-too-long
            ChatCommand.REMOVE_SERVER: r"^/remove_server\s+(?P<server_name>\S+)$",
            ChatCommand.LIST_SERVERS: r"^/list_servers$",
            ChatCommand.LIST_TOOLS: r"^/list_tools\s+(?P<server_name>\S+)$",
            ChatCommand.DESCRIBE_TOOL: (
                r"^/describe_tool\s+(?P<server_name>\S+)\s+(?P<tool_name>\S+)$"
            ),
            ChatCommand.QUIT: r"^/quit$",
        }

    def parse_command(
        self: "ChatInterface", user_input: str
    ) -> tuple[ChatCommand | None, dict[str, str]]:
        """Parse user input to identify commands and extract parameters.

        Parameters
        ----------
        user_input : str
            user provided input

        Returns
        -------
        ChatCommand | None
            identified command or None if no command is found
        dict[str, str]
            dictionary of command inputs extracted from user input
        """
        for command, command_pattern in self.command_patterns.items():
            match = re.match(command_pattern, user_input.strip())

            if match:
                return command, match.groupdict()

        return None, {}

    async def handle_command(  # noqa: C901, PLR0912
        self: "ChatInterface", command: ChatCommand, command_inputs: dict
    ) -> None:
        """Handle the command and provide appropriate responses.

        Parameters
        ----------
        command : ChatCommand
            user provided specific command
        command_inputs : dict
            dictionary of command inputs extracted from user input
        """
        match command:
            case ChatCommand.HELP:
                bot_response(f"Available commands: {HELP_MESSAGE}")
            case ChatCommand.ADD_SERVER:
                server_name: str = command_inputs["server_name"]
                server_url: str = command_inputs["server_url"]
                server_headers: str = command_inputs["server_headers"]

                try:
                    parsed_server_headers: dict = (
                        json.loads(server_headers) if server_headers else {}
                    )
                except json.JSONDecodeError:
                    bot_response("Invalid headers format. Please provide a valid JSON object.")

                    return

                addition_status, server_tools = await self.mcp_client.add_mcp_server(
                    server_name, server_url, server_headers=parsed_server_headers
                )

                if addition_status == Status.FAILURE:
                    bot_response(f"MCP server {server_name} addition status: {addition_status}.")
                elif server_tools:
                    bot_response(f"Added tools from MCP server {server_name}: {server_tools}.")
                else:
                    bot_response(f"No tools in MCP server {server_name}.")
            case ChatCommand.REMOVE_SERVER:
                server_name: str = command_inputs["server_name"]

                removal_status = self.mcp_client.remove_mcp_server(server_name)

                bot_response(f"MCP server {server_name} removal status: {removal_status}.")
            case ChatCommand.LIST_SERVERS:
                servers = self.mcp_client.list_mcp_servers()

                if servers:
                    bot_response(servers)
                else:
                    bot_response("No MCP servers configured.")
            case ChatCommand.LIST_TOOLS:
                server_name: str = command_inputs["server_name"]

                listing_status, server_tools = self.mcp_client.list_mcp_server_tools(server_name)

                if listing_status == Status.FAILURE:
                    bot_response(
                        f"MCP server {server_name} tools listing status: {listing_status}."
                    )
                elif server_tools:
                    bot_response(
                        f"Available tools for MCP server {server_name}: {', '.join(server_tools)}"
                    )
                else:
                    bot_response(f"No tools in MCP server {server_name}.")
            case ChatCommand.DESCRIBE_TOOL:
                server_name: str = command_inputs["server_name"]
                tool_name: str = command_inputs["tool_name"]

                description_status, tool_description = self.mcp_client.describe_mcp_server_tool(
                    server_name, tool_name
                )

                if description_status == Status.FAILURE:
                    bot_response(f"Missing tool {tool_name} in MCP server {server_name}.")
                else:
                    bot_response(tool_description)
            case ChatCommand.QUIT:
                bot_response("Bye.")

                sys.exit()

    async def start_interactive_chat(self: "ChatInterface") -> None:
        """Manage the interactive chat loop."""
        bot_response("Type '/help' to see more information.")

        while True:
            user_input = await user_prompt()

            command, command_inputs = self.parse_command(user_input)

            if command:
                await self.handle_command(command, command_inputs)

                continue

            with self.langfuse_client.start_as_current_observation(
                name="interactive chat", as_type="span", end_on_exit=True
            ) as span_monitoring:
                span_monitoring.update(input=user_input)

                llm_output = await llm_response(
                    self.llm_orchestrator.process_user_message(user_input)
                )

                span_monitoring.update(output=llm_output)


def main() -> None:
    """Define the main entry point for the chat interface."""
    settings = Configurations()

    initiate_logging(settings)

    chat_interface = ChatInterface(settings)

    asyncio.run(chat_interface.start_interactive_chat())


if __name__ == "__main__":
    main()
