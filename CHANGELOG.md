# Changelog

## v0.3.0 - 2026-10-17

- Moved the project baseline to Python 3.14 and aligned runtime, packaging metadata, and development tooling with that target.
- Updated server and client compatibility for newer FastMCP and MCP model conventions while keeping required legacy behavior.
- Reworked server observability by replacing per-tool wrappers with middleware-based tool-call logging and shared logging bootstrap utilities.
- Updated expression/sampling-related server behavior together with client orchestration and tool-call handling.
- Updated the MCP Registry manifest and publishing workflow for the v0.3.0 package release.

## v0.2.0 - 2025-11-09

- Introduced MCP Registry metadata and a dedicated publishing workflow for distribution.
- Added a PyPI-focused README to improve package presentation and release clarity.
- Updated release automation and quality-hook configuration to strengthen the release pipeline.
- Refreshed dependency and package metadata to support the 0.2.0 release baseline.

## v0.1.0 - 2025-10-04

- Introduced release automation for packaging and distribution.
- Added governance and security documents to formalize project standards.
- Promoted package metadata for public release readiness (beta classifier, project URLs, and removal of private-upload classifier markers).
- Updated dependency and lockfile metadata as part of release stabilization.

## v0.0.6 - 2025-10-03

- Introduced a docs site foundation and CI workflows for documentation and code quality.
- Added contribution and license documentation to support project collaboration and compliance.
- Refactored client structure by introducing a dedicated client module and reducing orchestration complexity.
- Updated monitoring behavior and arithmetic-related server/client paths.

## v0.0.5 - 2025-09-06

- Added a structured client utilities package for console, dependency, and monitoring concerns.
- Reorganized configuration and logging-related code into clearer utility boundaries.
- Updated server startup and configuration behavior.
- Refreshed dependency and development-tooling configuration for the new structure.

## v0.0.4 - 2025-08-30

- Improved progress handling across client orchestration and server operations.
- Updated expression-related server behavior and wiring for simplification/exponentiation flows.
- Refined client and console-side behavior supporting the updated progress model.
- Refreshed dependency constraints and lockfile state.

## v0.0.3 - 2025-08-10

- Added exponentiation support on the server side.
- Expanded client orchestration and LLM interaction behavior for multi-step execution.
- Updated server configuration and simplification logic.
- Refreshed project and tooling metadata to support the expanded feature set.

## v0.0.2 - 2025-07-27

- Added an expression simplification tool to the MCP server.
- Improved server registration/wiring around arithmetic tool flows.
- Updated client execution flow for tool invocation handling.
- Refreshed dependency metadata and lockfile state.

## v0.0.1 - 2025-07-27

- Initial public release of the MCP learning project with runnable server and client components.
- Shipped command-line entry points for both sides (`mcp-server` and `mcp-client`) to make local experimentation straightforward.
- Introduced an MCP server exposing core arithmetic operations and inverse-operation tools.
- Added an interactive chat-style client flow for invoking MCP tools and exploring request/response behavior.
- Established baseline package metadata, dependency setup, and foundational documentation.
