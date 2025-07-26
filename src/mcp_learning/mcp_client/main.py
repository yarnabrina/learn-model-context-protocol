"""Initialise the chat interface for the MCP client."""

import asyncio
import enum
import functools
import re
import sys

from .configurations import Configurations
from .console import bot_response, llm_response, user_prompt
from .orchestrator import MCPClient, OpenAIOrchestrator

HELP_MESSAGE = """
/help
    Show this help message.

/add_server <server_name> <server_url>
    Add/register a new MCP server.

/remove_server <server_name>
    Remove an existing MCP server.

/list_servers
    List all configured MCP servers.

/list_tools <server_name>
    List available tools for a specific server.

/describe_tool <server_name> <tool_name>
    Show details for a specific tool on a server.

/quit
    Exit the chat.
"""

SYSTEM_PROMPT = f"""You are a helpful assistant.

You help users to interact with the available tools. You can provide information about the tools, call the tools, and assist users in their tasks. You can also chat with users to understand their requirements and provide them with the necessary information.

If necessary tools are unavailable, you do not try to solve on your own and inform users about lack of current capability.

The following options are available to user. If you detect a message is passed to you by mistake or because of typo, identify the users intent and prompt them with the correction.

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
    mcp_client : MCPClient
        client for managing MCP servers and their tools
    llm_orchestrator : OpenAIOrchestrator
        orchestrator instance for handling language model interactions
    """

    def __init__(self: "ChatInterface", settings: Configurations) -> None:
        self.settings = settings

        self.mcp_client = MCPClient(settings)
        self.llm_orchestrator = OpenAIOrchestrator(self.mcp_client, self.settings)

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
            ChatCommand.ADD_SERVER: r"^/add_server\s+(?P<server_name>\S+)\s+(?P<server_url>\S+)$",
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

    async def handle_command(  # noqa: C901
        self: "ChatInterface", command: ChatCommand, command_inputs: dict[str, str]
    ) -> None:
        """Handle the command and provide appropriate responses.

        Parameters
        ----------
        command : ChatCommand
            user provided specific command
        command_inputs : dict[str, str]
            dictionary of command inputs extracted from user input
        """
        match command:
            case ChatCommand.HELP:
                bot_response(f"Available commands: {HELP_MESSAGE}")
            case ChatCommand.ADD_SERVER:
                server_tools = await self.mcp_client.add_mcp_server(
                    command_inputs["server_name"], command_inputs["server_url"]
                )

                if server_tools:
                    bot_response(f"Added tools from MCP server: {server_tools}.")
            case ChatCommand.REMOVE_SERVER:
                removal_status = self.mcp_client.remove_mcp_server(command_inputs["server_name"])

                bot_response(f"MCP server removal status: {removal_status}.")
            case ChatCommand.LIST_SERVERS:
                bot_response(self.mcp_client.list_mcp_servers())
            case ChatCommand.LIST_TOOLS:
                server_tools = self.mcp_client.list_mcp_server_tools(command_inputs["server_name"])

                if server_tools:
                    bot_response(
                        f"Available tools for {command_inputs['server_name']}:"
                        f" {', '.join(server_tools)}"
                    )
            case ChatCommand.DESCRIBE_TOOL:
                tool_description = self.mcp_client.describe_mcp_server_tool(
                    command_inputs["server_name"], command_inputs["tool_name"]
                )

                if tool_description:
                    bot_response(tool_description)
            case ChatCommand.QUIT:
                bot_response("Bot: Bye.")

                sys.exit()

    async def start_interactive_chat(self: "ChatInterface") -> None:
        """Manage the interactive chat loop."""
        bot_response("Type '/help' to see more information.")

        while True:
            user_input = user_prompt()

            command, command_inputs = self.parse_command(user_input)

            if command:
                await self.handle_command(command, command_inputs)

                continue

            async for (
                assistant_message_token,
                initial_token,
            ) in self.llm_orchestrator.process_user_message(user_input):
                llm_response(assistant_message_token, start=initial_token)


def main() -> None:
    """Define the main entry point for the chat interface."""
    settings = Configurations()
    chat_interface = ChatInterface(settings)

    asyncio.run(chat_interface.start_interactive_chat())


if __name__ == "__main__":
    main()
