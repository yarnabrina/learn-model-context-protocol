# Using `pip` Instead of `uv` in This Project

This project uses [`uv`](https://github.com/astral-sh/uv) in documentation and examples for speed and reproducibility, but you can do everything with `pip` and standard Python commands.

## Installation

What `uv sync` does is it creates a virtual environment (if not already created) and installs the dependencies listed in `pyproject.toml` along with the project itself. So, to replicate that with `pip`, you can do:

```shell
# Create a virtual environment (if not already created)
python3.13 -m venv .venv

# Activate the virtual environment
# On Windows
.venv\Scripts\activate
# On Unix or MacOS
# source .venv/bin/activate

# Upgrade pip and install dependencies (optional but recommended)
pip install --upgrade pip setuptools wheel

# Install the project and its main dependencies
pip install .

# Optional: Install extra dependencies as needed
# For enhanced CLI features (`prompt-toolkit`)
# pip install .[cli]
# For tracking and monitoring (`langfuse`)
# pip install .[monitoring]
# For all optional dependencies
# pip install ".[cli,monitoring]"
```

## Running the MCP Server and Client

The package provides two command-line entry points: `mcp-server` and `mcp-client`. You can run these commands directly after installation.

```shell
# Running the MCP Server
mcp-server --log_level INFO

# Running the MCP Client
mcp-client --language_model "gpt-4.1" azure_openai --azure_openai_endpoint "<YOUR-ENDPOINT-URL>" --azure_openai_deployment_name "gpt-4.1" --azure_openai_api_version "2025-01-01-preview" --azure_openai_api_key "<YOUR-API-KEY>"
```
