"""Provide functionality to raise a number to a power."""

import typing

import pydantic
from mcp.server.fastmcp import Context

from .arithmetic_operations import IdentityElements, multiply_numbers


class ExponentCorrection(pydantic.BaseModel):
    """Define supported type for exponent."""

    corrected_exponent: typing.Annotated[int, pydantic.Field(ge=1)] = pydantic.Field(
        description="natural number exponent for exponentiation operation"
    )


class ExponentiationResult(pydantic.BaseModel):
    """Define result of exponentiation operation."""

    power: float


@pydantic.validate_call(validate_return=True)
async def exponentiate(base: float, exponent: float, context: Context) -> ExponentiationResult:
    """Raise the base to the power of the exponent.

    Parameters
    ----------
    base : float
        number to be raised
    exponent : float
        number to raise to
    context : Context
        the context of the MCP server, used for logging and session management

    Returns
    -------
    ExponentiationResult
        power of `base` raised to `exponent`

    Raises
    ------
    NotImplementedError
        if the exponent is not a positive integer
    """
    if not exponent.is_integer() or exponent < 0:
        await context.info(f"Starting elicitation to correct {exponent=}.")

        elicitation_result = await context.elicit(
            f"Provided {exponent=} is not a natural number, and currently unsupported.",
            ExponentCorrection,
        )

        await context.info(f"Completed elicitation with {elicitation_result=}.")

        match elicitation_result.action:
            case "accept":
                exponent = elicitation_result.data.corrected_exponent
            case "decline" | "cancel":
                raise NotImplementedError("Only natural number powers are currently supported.")

    power_result = IdentityElements.MULTIPLICATIVE_IDENTITY
    for _ in range(int(exponent)):
        power_result = multiply_numbers(power_result, base).product

    return ExponentiationResult(power=power_result)


__all__ = ["ExponentCorrection", "ExponentiationResult", "exponentiate"]
