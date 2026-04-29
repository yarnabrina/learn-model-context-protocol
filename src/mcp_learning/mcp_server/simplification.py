"""Provide functionality to parse and solve arithmetic expressions from natural language."""

import enum
import typing

import pydantic
from fastmcp import Context
from mcp.types import SamplingMessage, TextContent

from .arithmetic_operations import add_numbers, divide_numbers, multiply_numbers, subtract_numbers


@pydantic.validate_call(validate_return=True)
async def parse_arithmetic_expression(text: str, context: Context) -> str:
    """Parse a text into a valid arithmetic expression.

    Parameters
    ----------
    text : str
        text to parse into an arithmetic expression
    context : Context
        the context of the MCP server, used for logging and session management

    Returns
    -------
    str
        a valid arithmetic expression in reverse Polish notation

    Raises
    ------
    TypeError
        if the response content is not of type TextContent
    """
    await context.debug(f"Received parsing request for {text=}.")

    instruction = """You are a calculator assistant.

- Your task is to convert the given text into an arithmetic expression.
- Only addition, subtraction, multiplication and division are allowed in the expression.
- The expression should be a valid arithmetic expression that can be evaluated to a number.
- The expression should not contain any variables or functions.
- The expression should be in reverse Polish notation.

Return only the postfix arithmetic expression without any additional text or explanation.
"""
    await context.report_progress(1, total=2, message="Started MCP sampling.")

    response = await context.sample(
        [SamplingMessage(role="user", content=TextContent(type="text", text=f"Text: {text}"))],
        system_prompt=instruction,
        temperature=0,
        max_tokens=2048,
    )

    await context.report_progress(2, total=2, message="Finished MCP sampling.")

    content = response.text

    if not isinstance(content, str):
        await context.error(f"Expected response content to be text: {content=}.")

        raise TypeError(f"Response content is not a text content: {content=}.")

    expression = content.strip()

    await context.info(f"Completed parsing {text=} into {expression=}.")

    return expression


@enum.unique
class SimpleArithmeticOperator(enum.StrEnum):
    """Define supported arithmetic operators."""

    ADDITION = "+"
    SUBTRACTION = "-"
    MULTIPLICATION = "*"
    DIVISION = "/"


class InvalidOperatorError(Exception):
    """Raised when unsupported operators are encountered.

    Parameters
    ----------
    operator : str
        the unsupported operator that caused the error
    """

    def __init__(self: typing.Self, operator: str) -> None:
        super().__init__(f"Unsupported operator encountered: {operator=}.")


class InvalidExpressionError(Exception):
    """Raised when invalid arithmetic expressions are encountered.

    Parameters
    ----------
    expression : str
        the invalid expression that caused the error
    reason : str
        the reason why the expression is invalid
    """

    def __init__(self: typing.Self, expression: str, reason: str) -> None:
        super().__init__(f"Invalid arithmetic expression encountered: {expression=}, {reason=}.")


@pydantic.validate_call(validate_return=True)
async def evaluate_arithmetic_expression(expression: str) -> float:  # noqa: C901
    """Evaluate postfix arithmetic expression in reverse Polish notation.

    Parameters
    ----------
    expression : str
        elements of arithmetic expression in postfix format

    Returns
    -------
    float
        result of arithmetic expression

    Raises
    ------
    InvalidOperatorError
        if the expression contains an unsupported operator
    InvalidExpressionError
        if the expression is not a valid postfix arithmetic expression
    """
    stack: list[float] = []
    for token in expression.split():
        try:
            element = float(token)
        except ValueError:
            try:
                operator = SimpleArithmeticOperator(token)
            except ValueError as error:
                raise InvalidOperatorError(token) from error
        else:
            stack.append(element)

            continue

        if len(stack) < 2:  # noqa: PLR2004
            raise InvalidExpressionError(
                expression,
                f"operator {operator.value!r} requires two operands, found {len(stack)}",
            )

        second_input = stack.pop()
        first_input = stack.pop()

        match operator:
            case SimpleArithmeticOperator.ADDITION:
                result = add_numbers(first_input, second_input).sum
            case SimpleArithmeticOperator.SUBTRACTION:
                result = subtract_numbers(first_input, second_input).difference
            case SimpleArithmeticOperator.MULTIPLICATION:
                result = multiply_numbers(first_input, second_input).product
            case SimpleArithmeticOperator.DIVISION:
                result = divide_numbers(first_input, second_input).quotient

        stack.append(result)

    if len(stack) != 1:
        raise InvalidExpressionError(
            expression, f"expected exactly one final result, found {len(stack)} values"
        )

    return stack[0]


__all__ = [
    "InvalidExpressionError",
    "InvalidOperatorError",
    "SimpleArithmeticOperator",
    "evaluate_arithmetic_expression",
    "parse_arithmetic_expression",
]
