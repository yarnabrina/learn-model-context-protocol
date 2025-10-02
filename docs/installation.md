# Installation

Instructions for setting up the project environment and installing dependencies.

## Basic Setup

1. Clone the repository:

    ```shell
    git clone https://github.com/yarnabrina/learn-model-context-protocol.git mcp-exploration
    ```

2. Navigate to the project directory:

    ```shell
    cd mcp-exploration
    ```

3. Set up a virtual environment and install necessary dependencies:

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
