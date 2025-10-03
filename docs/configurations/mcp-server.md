# MCP Server

Documentation for configuring the MCP server.

```text
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
