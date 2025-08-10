"""Define fundamental arithmetic operations and their properties."""

import enum

import pydantic


@enum.unique
class IdentityElements(enum.IntEnum):
    """Define assumed identity elements."""

    ADDITIVE_IDENTITY = 0
    MULTIPLICATIVE_IDENTITY = 1


class AdditionResult(pydantic.BaseModel):
    """Define result of addition operation."""

    sum: float


@pydantic.validate_call(validate_return=True)
def add_numbers(left_addend: float, right_addend: float) -> AdditionResult:
    """Perform addition of two real numbers.

    Parameters
    ----------
    left_addend : float
        first number to be added
    right_addend : float
        second number to be added

    Returns
    -------
    AdditionResult
        sum of `left_addend` and `right_addend`

    Examples
    --------
    .. code-block:: pycon

        >>> from mcp_server.arithmetic_operations import add_numbers
        >>> add_numbers(1, 2)
        AdditionResult(sum=3.0)
        >>> add_numbers(1, -2)
        AdditionResult(sum=-1.0)
        >>> add_numbers(-1, 2)
        AdditionResult(sum=1.0)
        >>> add_numbers(-1, -2)
        AdditionResult(sum=-3.0)
    """
    sum_of_two_numbers = left_addend + right_addend

    return AdditionResult(sum=sum_of_two_numbers)


class MultiplicationResult(pydantic.BaseModel):
    """Define result of multiplication operation."""

    product: float


@pydantic.validate_call(validate_return=True)
def multiply_numbers(multiplicand: float, multiplier: float) -> MultiplicationResult:
    """Perform multiplication of two real numbers.

    Parameters
    ----------
    multiplicand : float
        number to be multiplied
    multiplier : float
        number by which to multiply

    Returns
    -------
    MultiplicationResult
        product of `multiplicand` and `multiplier`

    Examples
    --------
    .. code-block:: pycon

        >>> from mcp_server.arithmetic_operations import multiply_numbers
        >>> multiply_numbers(1, 2)
        MultiplicationResult(product=2.0)
        >>> multiply_numbers(1, -2)
        MultiplicationResult(product=-2.0)
        >>> multiply_numbers(-1, 2)
        MultiplicationResult(product=-2.0)
        >>> multiply_numbers(-1, -2)
        MultiplicationResult(product=2.0)
    """
    product_of_two_numbers = multiplicand * multiplier

    return MultiplicationResult(product=product_of_two_numbers)


__all__ = [
    "AdditionResult",
    "IdentityElements",
    "MultiplicationResult",
    "add_numbers",
    "multiply_numbers",
]
