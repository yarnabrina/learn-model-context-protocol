"""Provide functionality to raise a number to a power."""

import pydantic
from mcp.server.fastmcp import Context

from .arithmetic_operations import IdentityElements, get_reciprocal, multiply_numbers


class ExponentCorrection(pydantic.BaseModel):
    """Define supported type for exponent."""

    corrected_exponent: int = pydantic.Field(
        description="integer exponent for exponentiation operation"
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
        if the exponent is not an integer
    NotImplementedError
        if the base is zero and the exponent is a negative integer
    ValueError
        if the base is zero and the exponent is zero
    ZeroDivisionError
        if the base is zero and the exponent is a negative integer
    """
    if not exponent.is_integer():
        await context.report_progress(1, total=2, message="Starting MCP elicitation.")

        elicitation_result = await context.elicit(
            f"Provided {exponent=} is not an integer, and currently unsupported.",
            ExponentCorrection,
        )

        await context.report_progress(1, total=2, message="Finished MCP elicitation.")

        match elicitation_result.action:
            case "accept":
                corrected_exponent = elicitation_result.data.corrected_exponent

                await context.debug(f"User corrected {exponent=} to {corrected_exponent}.")
            case "decline" | "cancel":
                await context.error(
                    f"User decided to {elicitation_result.action} the correction request."
                )

                raise NotImplementedError("Only integer powers are currently supported.")

        exponent = corrected_exponent

    if base == IdentityElements.ADDITIVE_IDENTITY.value == exponent:
        raise ValueError("0 raised to the power 0 is undefined.")

    if base == IdentityElements.ADDITIVE_IDENTITY.value and exponent < 0:
        raise ZeroDivisionError("0 raised to a negative power is undefined.")

    power_result = IdentityElements.MULTIPLICATIVE_IDENTITY.value
    for _ in range(int(abs(exponent))):
        power_result = multiply_numbers(power_result, base).product

    if exponent < 0:
        power_result = get_reciprocal(power_result).reciprocal

    return ExponentiationResult(power=power_result)


__all__ = ["ExponentCorrection", "ExponentiationResult", "exponentiate"]
