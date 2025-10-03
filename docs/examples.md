# Examples

This page showcases example sessions using the MCP server and client.

> **Note:** This project uses [`uv`](https://github.com/astral-sh/uv) in examples for speed and convenience, but `uv` is **not required**. You can use `pip` and standard Python commands instead. See [Dependency Management](dependency-management.md) for details.

## Starting the MCP Server

```shell
uv run mcp-server --log_level INFO
```

## Starting the MCP Client

> **Note:** Replace `<YOUR-ENDPOINT-URL>` and `<YOUR-API-KEY>` with your actual values.

```shell
uv run mcp-client --language_model "gpt-4.1" azure_openai --azure_openai_endpoint "<YOUR-ENDPOINT-URL>" --azure_openai_deployment_name "gpt-4.1" --azure_openai_api_version "2025-01-01-preview" --azure_openai_api_key "<YOUR-API-KEY>"
```

## Sample Session

Below is a sample interactive session with the MCP client. File paths and usernames have been anonymized for privacy.

```text
[Bot] Type '/help' to see more information.

[You] /help
[Bot] Available commands:
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


[You] Hi, what can you do?
[LLM] I can demonstrate the use of various tools available through MCP servers. These tools can perform tasks such as listing available servers, describing tools, adding or removing servers, and more.

If you'd like to see what commands are available, just type:
/help

Let me know what you'd like to try!

[You] /add_server math http://localhost:8000/mcp
INFO     Received session ID: 13950bfdfc994f5797c0f24da208f902
INFO     Negotiated protocol version: 2025-06-18
[Bot] Added tools from MCP server math: ['Add Numbers', 'Get Negative', 'Subtract Numbers', 'Multiply Numbers', 'Get Reciprocal', 'Divide Numbers',
'Parse Arithmetic Expression', 'Evaluate Arithmetic Expression', 'Power'].

[You] /list_tools math
[Bot] Available tools for MCP server math: addition, negation, subtraction, multiplication, reciprocal, division, parse_expression,
evaluate_expression, exponentiation

[You] /describe_tool math exponentiation
[Bot]
{
    'name': 'exponentiation',
    'display_name': 'Power',
    'title': 'Power',
    'description': 'Raise a base to an exponent',
    'input_schema': {
        'properties': {'base': {'title': 'Base', 'type': 'number'}, 'exponent': {'title': 'Exponent', 'type': 'number'}},
        'required': ['base', 'exponent'],
        'title': 'exponentiateArguments',
        'type': 'object'
    },
    'output_schema': {
        'description': 'Define result of exponentiation operation.',
        'properties': {'power': {'title': 'Power', 'type': 'number'}},
        'required': ['power'],
        'title': 'ExponentiationResult',
        'type': 'object'
    },
    'annotations': {'title': 'Exponentiation', 'readOnlyHint': True, 'destructiveHint': None, 'idempotentHint': None, 'openWorldHint': False},
    'server_name': 'math'
}

[You] Let's say, I've 5 mangoes and my brother has 3. If we want to redistribute equally, how should we formulate the problem?
[LLM] Great question! To redistribute the mangoes equally between you and your brother, you need to:

1. Add the total number of mangoes you both have.
2. Divide the total by 2 (since there are two people).

Let me demonstrate this using the available tools:

- First, I'll use the addition tool to sum 5 and 3.
- Then, I'll use the division tool to divide the total by 2.

Let’s proceed with these calculations.
INFO     Received session ID: bc69be9f25934ee6913d70faec8c8d78
INFO     Negotiated protocol version: 2025-06-18
INFO     Received session ID: 02e9b294a97d44ad98947440a94b771b
INFO     Negotiated protocol version: 2025-06-18
Here’s how the problem is formulated and solved using the tools:

1. Addition: 5 mangoes (you) + 3 mangoes (your brother) = 8 mangoes in total.
2. Division: 8 mangoes ÷ 2 people = 4 mangoes per person.

So, after redistribution, each of you should get 4 mangoes. This demonstrates how to use addition and division tools to solve the problem. If you want to see the step-by-step tool usage or try another scenario, let me know!

[You] Can you give this as an expression instead, before evaluation?
[LLM]
INFO     Received session ID: e86049390c88419b99424de03d3796fa
INFO     Negotiated protocol version: 2025-06-18
[Bot] Progress of call_lt0phM66QkWxVoxBlXVtKT7O: 1.0/2.0. Started MCP sampling..
[Bot] Progress of call_lt0phM66QkWxVoxBlXVtKT7O: 2.0/2.0. Finished MCP sampling..
You requested the expression before evaluation. The parsed arithmetic expression in postfix (reverse Polish) notation is:

5 3 + 2 /

This represents (5 + 3) divided by 2, ready for evaluation. If you want to see the evaluated result or another format, let me know!

[You] Good, now evaluate this expression as is.
[LLM]
INFO     Received session ID: 54c9771e4b8a4e48a65e3c47ca96c003
INFO     Negotiated protocol version: 2025-06-18
The evaluated result of the expression 5 3 + 2 / is:

4.0

This confirms that each person should get 4 mangoes after redistribution. If you have more expressions to evaluate or want to try other math operations, just let me know!

[You] Just curious, can you tell what is cube of that?
[LLM]
INFO     Received session ID: 06196fbf20c94aa39f1dda84cbd59c4e
INFO     Negotiated protocol version: 2025-06-18
The cube of 4 (which is 4^3) is:

64.0

If you want to explore more powers or other mathematical operations, feel free to ask!

[You] Nice, let's find out it's square root.
[LLM]
INFO     Received session ID: 137be44a84cf44dcadb7e2e2ec2978f4
INFO     Negotiated protocol version: 2025-06-18
[Bot] Progress of call_b9UIJ31j5YJ8K849adJ9t1pV: 1.0/2.0. Starting MCP elicitation..
[Bot] Thank you for your response! The MCP server has indicated that the exponent value you provided (0.5) is not supported because it is not an
integer. To proceed, the server needs you to provide an integer value for the exponent.

Could you please specify an integer exponent for the exponentiation operation? For example, you might enter 2, 3, or any other whole number.

[You] Hmm, okay, let's ignore then.
[Bot] Progress of call_b9UIJ31j5YJ8K849adJ9t1pV: 1.0/2.0. Finished MCP elicitation..
ERROR    User decided to decline the correction request.
WARNING  Failed tool call to tool_name='mcp-math-exponentiation' with arguments={'base': 64, 'exponent': 0.5}: Error executing tool exponentiation:
         Only integer powers are currently supported..
The tool call to find the square root of 64 (using exponent 0.5) failed because the exponentiation tool currently only supports integer exponents.

However, mathematically, the square root of 64 is 8.

If you want to try other integer exponents or need help with another calculation, let me know!

[You] How do I disconnect the servers added?
[LLM] To disconnect or remove servers that have been added, you can use the following command:

/remove_server <server_name>

Just replace <server_name> with the name of the server you want to remove. If you’d like to see a list of all currently configured servers, you can use:

/list_servers

Let me know if you want to see the list or need help with a specific server removal!

[You] /remove_server math
[Bot] MCP server math removal status: success.

[You] /quit
[Bot] Bye.
```

If you're interested, you can see the MCP server interactions here:

```text
[10/02/25 23:07:30] INFO     Created new transport with session ID: 13950bfdfc994f5797c0f24da208f902                     streamable_http_manager.py:233
INFO:     127.0.0.1:53308 - "POST /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53311 - "GET /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53312 - "POST /mcp HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:53315 - "POST /mcp HTTP/1.1" 200 OK
[10/02/25 23:07:31] INFO     Processing request of type ListToolsRequest                                                                  server.py:664
                    INFO     Terminating session: 13950bfdfc994f5797c0f24da208f902                                               streamable_http.py:630
INFO:     127.0.0.1:53317 - "DELETE /mcp HTTP/1.1" 200 OK
[10/02/25 23:11:47] INFO     Created new transport with session ID: bc69be9f25934ee6913d70faec8c8d78                     streamable_http_manager.py:233
INFO:     127.0.0.1:53780 - "POST /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53783 - "POST /mcp HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:53784 - "GET /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53786 - "POST /mcp HTTP/1.1" 200 OK
[10/02/25 23:11:48] INFO     Processing request of type CallToolRequest                                                                   server.py:664
                    INFO     Received tool call for tool_name='addition' with args=(), kwargs={'left_addend': 5.0, 'right_addend': 3.0}.     main.py:61
                    INFO     Succeeded tool call for tool_name='addition' with result=AdditionResult(sum=8.0).                               main.py:77
INFO:     127.0.0.1:53788 - "POST /mcp HTTP/1.1" 200 OK
                    INFO     Processing request of type ListToolsRequest                                                                  server.py:664
                    INFO     Terminating session: bc69be9f25934ee6913d70faec8c8d78                                               streamable_http.py:630
INFO:     127.0.0.1:53790 - "DELETE /mcp HTTP/1.1" 200 OK
                    INFO     Created new transport with session ID: 02e9b294a97d44ad98947440a94b771b                     streamable_http_manager.py:233
INFO:     127.0.0.1:53792 - "POST /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53795 - "GET /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53796 - "POST /mcp HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:53801 - "POST /mcp HTTP/1.1" 200 OK
[10/02/25 23:11:49] INFO     Processing request of type CallToolRequest                                                                   server.py:664
                    INFO     Received tool call for tool_name='division' with args=(), kwargs={'dividend': 8.0, 'divisor': 2.0}.             main.py:61
                    INFO     Succeeded tool call for tool_name='division' with result=DivisionResult(quotient=4.0).                          main.py:77
INFO:     127.0.0.1:53803 - "POST /mcp HTTP/1.1" 200 OK
                    INFO     Processing request of type ListToolsRequest                                                                  server.py:664
[10/02/25 23:11:50] INFO     Terminating session: 02e9b294a97d44ad98947440a94b771b                                               streamable_http.py:630
INFO:     127.0.0.1:53805 - "DELETE /mcp HTTP/1.1" 200 OK
[10/02/25 23:12:56] INFO     Created new transport with session ID: e86049390c88419b99424de03d3796fa                     streamable_http_manager.py:233
INFO:     127.0.0.1:53935 - "POST /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53939 - "GET /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53938 - "POST /mcp HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:53941 - "POST /mcp HTTP/1.1" 200 OK
                    INFO     Processing request of type CallToolRequest                                                                   server.py:664
                    INFO     Received tool call for tool_name='parse_expression' with args=(), kwargs={'text': '(5 + 3) / 2', 'context':     main.py:61
                             Context()}.
INFO:     127.0.0.1:53948 - "POST /mcp HTTP/1.1" 202 Accepted
[10/02/25 23:12:58] INFO     Succeeded tool call for tool_name='parse_expression' with result='5 3 + 2 /'.                                   main.py:77
INFO:     127.0.0.1:53950 - "POST /mcp HTTP/1.1" 200 OK
[10/02/25 23:12:59] INFO     Processing request of type ListToolsRequest                                                                  server.py:664
                    INFO     Terminating session: e86049390c88419b99424de03d3796fa                                               streamable_http.py:630
INFO:     127.0.0.1:53952 - "DELETE /mcp HTTP/1.1" 200 OK
[10/02/25 23:13:34] INFO     Created new transport with session ID: 54c9771e4b8a4e48a65e3c47ca96c003                     streamable_http_manager.py:233
INFO:     127.0.0.1:54017 - "POST /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:54020 - "GET /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:54021 - "POST /mcp HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:54025 - "POST /mcp HTTP/1.1" 200 OK
[10/02/25 23:13:35] INFO     Processing request of type CallToolRequest                                                                   server.py:664
                    INFO     Received tool call for tool_name='evaluate_expression' with args=(), kwargs={'expression': '5 3 + 2 /'}.        main.py:61
                    INFO     Succeeded tool call for tool_name='evaluate_expression' with result=4.0.                                        main.py:77
INFO:     127.0.0.1:54027 - "POST /mcp HTTP/1.1" 200 OK
                    INFO     Processing request of type ListToolsRequest                                                                  server.py:664
                    INFO     Terminating session: 54c9771e4b8a4e48a65e3c47ca96c003                                               streamable_http.py:630
INFO:     127.0.0.1:54029 - "DELETE /mcp HTTP/1.1" 200 OK
[10/02/25 23:14:57] INFO     Created new transport with session ID: 06196fbf20c94aa39f1dda84cbd59c4e                     streamable_http_manager.py:233
INFO:     127.0.0.1:54190 - "POST /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:54196 - "GET /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:54195 - "POST /mcp HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:54198 - "POST /mcp HTTP/1.1" 200 OK
[10/02/25 23:14:58] INFO     Processing request of type CallToolRequest                                                                   server.py:664
                    INFO     Received tool call for tool_name='exponentiation' with args=(), kwargs={'base': 4.0, 'exponent': 3.0,           main.py:61
                             'context': Context()}.
                    INFO     Succeeded tool call for tool_name='exponentiation' with result=ExponentiationResult(power=64.0).                main.py:77
INFO:     127.0.0.1:54200 - "POST /mcp HTTP/1.1" 200 OK
                    INFO     Processing request of type ListToolsRequest                                                                  server.py:664
                    INFO     Terminating session: 06196fbf20c94aa39f1dda84cbd59c4e                                               streamable_http.py:630
INFO:     127.0.0.1:54202 - "DELETE /mcp HTTP/1.1" 200 OK
[10/02/25 23:15:19] INFO     Created new transport with session ID: 137be44a84cf44dcadb7e2e2ec2978f4                     streamable_http_manager.py:233
INFO:     127.0.0.1:54243 - "POST /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:54247 - "POST /mcp HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:54246 - "GET /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:54249 - "POST /mcp HTTP/1.1" 200 OK
[10/02/25 23:15:20] INFO     Processing request of type CallToolRequest                                                                   server.py:664
                    INFO     Received tool call for tool_name='exponentiation' with args=(), kwargs={'base': 64.0, 'exponent': 0.5,          main.py:61
                             'context': Context()}.
INFO:     127.0.0.1:54283 - "POST /mcp HTTP/1.1" 202 Accepted
[10/02/25 23:15:38] ERROR    Failed tool call for tool_name='exponentiation'.                                                                main.py:73
                             ╭───────────────────────────────────── Traceback (most recent call last) ─────────────────────────────────────╮
                             │ C:\Users\<YOUR-USERNAME>\path\to\repo\mcp-exploration\src\mcp_learning\mcp_server\main.py:65 in logged_tool │
                             │                                                                                                             │
                             │    62 │   │                                                                                                 │
                             │    63 │   │   try:                                                                                          │
                             │    64 │   │   │   if asyncio.iscoroutinefunction(tool_callable):                                            │
                             │ ❱  65 │   │   │   │   result = await tool_callable(*args, **kwargs)                                         │
                             │    66 │   │   │   else:                                                                                     │
                             │    67 │   │   │   │   result = tool_callable(*args, **kwargs)                                               │
                             │    68 │   │   except ExceptionGroup:                                                                        │
                             │                                                                                                             │
                             │ C:\Users\<YOUR-USERNAME>\path\to\repo\mcp-exploration\.venv\Lib\site-packages\pydantic\_internal\_validate_ │
                             │ call.py:34 in wrapper_function                                                                              │
                             │                                                                                                             │
                             │    31 │   │                                                                                                 │
                             │    32 │   │   @functools.wraps(wrapped)                                                                     │
                             │    33 │   │   async def wrapper_function(*args, **kwargs):  # type: ignore                                  │
                             │ ❱  34 │   │   │   return await wrapper(*args, **kwargs)                                                     │
                             │    35 │   else:                                                                                             │
                             │    36 │   │                                                                                                 │
                             │    37 │   │   @functools.wraps(wrapped)                                                                     │
                             │                                                                                                             │
                             │ C:\Users\<YOUR-USERNAME>\path\to\repo\mcp-exploration\.venv\Lib\site-packages\pydantic\_internal\_validate_ │
                             │ call.py:122 in return_val_wrapper                                                                           │
                             │                                                                                                             │
                             │   119 │   │   │   if inspect.iscoroutinefunction(self.function):                                            │
                             │   120 │   │   │   │                                                                                         │
                             │   121 │   │   │   │   async def return_val_wrapper(aw: Awaitable[Any]) -> None:                             │
                             │ ❱ 122 │   │   │   │   │   return validator.validate_python(await aw)                                        │
                             │   123 │   │   │   │                                                                                         │
                             │   124 │   │   │   │   self.__return_pydantic_validator__ = return_val_wrapper                               │
                             │   125 │   │   │   else:                                                                                     │
                             │                                                                                                             │
                             │ C:\Users\<YOUR-USERNAME>\path\to\repo\mcp-exploration\src\mcp_learning\mcp_server\exponentiation.py:72 in   │
                             │ exponentiate                                                                                                │
                             │                                                                                                             │
                             │   69 │   │   │   │   │   f"User decided to {elicitation_result.action} the correction                       │
                             │      request."                                                                                              │
                             │   70 │   │   │   │   )                                                                                      │
                             │   71 │   │   │   │                                                                                          │
                             │ ❱ 72 │   │   │   │   raise NotImplementedError("Only integer powers are currently                           │
                             │      supported.")                                                                                           │
                             │   73 │   │                                                                                                  │
                             │   74 │   │   exponent = corrected_exponent                                                                  │
                             │   75                                                                                                        │
                             ╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                             NotImplementedError: Only integer powers are currently supported.
                    INFO     Terminating session: 137be44a84cf44dcadb7e2e2ec2978f4                                               streamable_http.py:630
INFO:     127.0.0.1:54285 - "DELETE /mcp HTTP/1.1" 200 OK
```
