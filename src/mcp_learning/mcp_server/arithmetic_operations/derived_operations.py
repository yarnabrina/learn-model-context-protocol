"""Define derived arithmetic operations using fundamental operations and their properties."""

import pydantic

from .axioms import add_numbers, get_negative, get_reciprocal, multiply_numbers


class SubtractionResult(pydantic.BaseModel):
    """Define result of subtraction operation."""

    difference: float


@pydantic.validate_call(validate_return=True)
def subtract_numbers(minuend: float, subtrahend: float) -> SubtractionResult:
    """Perform subtraction of two real numbers.

    Parameters
    ----------
    minuend : float
        number which is subtracted from
    subtrahend : float
        number which is subtracted

    Returns
    -------
    SubtractionResult
        difference of `minuend` from `subtrahend`

    Examples
    --------
    .. code-block:: pycon

        >>> from mcp_server.arithmetic_operations import subtract_numbers
        >>> subtract_numbers(1, 2)
        SubtractionResult(difference=-1.0)
        >>> subtract_numbers(1, -2)
        SubtractionResult(difference=3.0)
        >>> subtract_numbers(-1, 2)
        SubtractionResult(difference=-3.0)
        >>> subtract_numbers(-1, -2)
        SubtractionResult(difference=1.0)
    """
    difference_of_two_numbers = add_numbers(minuend, get_negative(subtrahend).negative)

    return SubtractionResult(difference=difference_of_two_numbers.sum)


class DivisionResult(pydantic.BaseModel):
    """Define result of division operation."""

    quotient: float


@pydantic.validate_call(validate_return=True)
def divide_numbers(dividend: float, divisor: float) -> DivisionResult:
    """Perform division of two real numbers.

    Parameters
    ----------
    dividend : float
        number which is divided
    divisor : float
        number which divides

    Returns
    -------
    DivisionResult
        quotient of `dividend` by `divisor`

    Examples
    --------
    .. code-block:: pycon

        >>> from mcp_server.arithmetic_operations import divide_numbers
        >>> divide_numbers(1, 2)
        DivisionResult(quotient=0.5)
        >>> divide_numbers(1, -2)
        DivisionResult(quotient=-0.5)
        >>> divide_numbers(-1, 2)
        DivisionResult(quotient=-0.5)
        >>> divide_numbers(-1, -2)
        DivisionResult(quotient=0.5)
    """
    quotient_of_two_numbers = multiply_numbers(dividend, get_reciprocal(divisor).reciprocal)

    return DivisionResult(quotient=quotient_of_two_numbers.product)


__all__ = ["DivisionResult", "SubtractionResult", "divide_numbers", "subtract_numbers"]
