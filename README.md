# Learning Model Context Protocol

Exploring different features of MCP servers and clients

## License

This project is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).

Copyright (C) 2025 Anirban Ray

See the [LICENSE](LICENSE) file for details.

## Usage

1. Clone the repository:

    ```shell
    git clone https://github.com/yarnabrina/learn-model-context-protocol.git mcp-exploration
    ```

2. Navigate to the project directory:

    ```shell
    cd mcp-exploration
    ```

3. Setup virtual environment and install necessary dependencies:

    ```shell
    uv sync
    ```

    Alternatively, you can install optional dependencies for enhanced functionality:

    ```shell
    # For enhanced CLI features (`prompt-toolkit`)
    # uv sync --extra cli

    # For tracking and monitoring (`langfuse`)
    # uv sync --extra monitoring

    # For all optional dependencies
    uv sync --all-extras
    ```

4. To run the MCP server, these are the available options:

    ```shell
    uv run mcp-server --help
    # usage: mcp-server [-h] [--streamable_http_path str] [--json_response | --no-json_response]
    #                 [--stateless_http | --no-stateless_http] [--host str] [--port int] [--debug | --no-debug]
    #                 [--log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
    #
    # Aggregate all configurations for the MCP server.
    #
    # options:
    # -h, --help            show this help message and exit
    # --streamable_http_path str
    #                         (default: /mcp)
    # --json_response, --no-json_response
    #                         (default: False)
    # --stateless_http, --no-stateless_http
    #                         (default: False)
    # --host str            (default: 127.0.0.1)
    # --port int            (default: 8000)
    # --debug, --no-debug   (default: False)
    # --log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
    #                         (default: WARNING)
    ```

5. To run the MCP client, following options are available:

    ```shell
    uv run mcp-client --help
    # usage: mcp-client [-h] [--sampling | --no-sampling] [--elicitation | --no-elicitation] [--logging | --no-logging] [--progress | --no-progress]
    #                   [--debug | --no-debug] [--log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--log_file {str,null}] [--language_model str]
    #                   [--language_model_max_tokens int] [--language_model_temperature float] [--language_model_top_p float] [--language_model_timeout int]
    #                   [--langfuse_enabled | --no-langfuse_enabled] [--langfuse_host {str,null}] [--langfuse_public_key {str,null}] [--langfuse_secret_key {str,null}]
    #                   {azure_openai,hosted_openai,openai} ...
    #
    # Aggregate all configurations for the MCP client.
    #
    # options:
    #   -h, --help            show this help message and exit
    #   --sampling, --no-sampling
    #                         (default: True)
    #   --elicitation, --no-elicitation
    #                         (default: True)
    #   --logging, --no-logging
    #                         (default: True)
    #   --progress, --no-progress
    #                         (default: True)
    #   --debug, --no-debug   (default: False)
    #   --log_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
    #                         (default: WARNING)
    #   --log_file {str,null}
    #                         (default: mcp_client.log)
    #   --language_model str  (default: gpt-4o-mini)
    #   --language_model_max_tokens int
    #                         (default: 4096)
    #   --language_model_temperature float
    #                         (default: 0.1)
    #   --language_model_top_p float
    #                         (default: 0.9)
    #   --language_model_timeout int
    #                         (default: 300)
    #   --langfuse_enabled, --no-langfuse_enabled
    #                         (default: False)
    #   --langfuse_host {str,null}
    #                         (default: null)
    #   --langfuse_public_key {str,null}
    #                         (default: null)
    #   --langfuse_secret_key {str,null}
    #                         (default: null)
    #
    # subcommands:
    #   {azure_openai,hosted_openai,openai}
    #     azure_openai
    #     hosted_openai
    #     openai
    ```

    The subcommands further give configurations for different LLM providers. For example:

    ```shell
    uv run mcp-client hosted_openai --help
    # usage: mcp-client hosted_openai [-h] [--language_model_provider_type hosted_openai] [--hosted_openai_api_key str] [--hosted_openai_base_url str]
    #                                 [--hosted_openai_headers {dict,null}]
    #
    # Define configurations for Hosted OpenAI.
    #
    # options:
    #   -h, --help            show this help message and exit
    #   --language_model_provider_type hosted_openai
    #                         (default: hosted_openai)
    #   --hosted_openai_api_key str
    #                         (required)
    #   --hosted_openai_base_url str
    #                         (required)
    #   --hosted_openai_headers {dict,null}
    #                         (default: null)
    ```
