"""Define inverse elements and their properties."""

import enum

import pydantic

from .fundamental_operations import IdentityElements


@enum.unique
class InverseElements(enum.IntEnum):
    """Define supported inverse elements."""

    ADDITIVE_INVERSE = -1
    MULTIPLICATIVE_INVERSE = 1


class DivisionByZeroError(Exception):
    """Raised when multiplicative inverse is attempted on additive identity."""

    def __init__(self: "DivisionByZeroError") -> None:
        super().__init__("Multiplicative inverse is not defined for additive identity.")


class NegativeResult(pydantic.BaseModel):
    """Define result of negative operation."""

    negative: float


@pydantic.validate_call(validate_return=True)
def get_negative(input_number: float) -> NegativeResult:
    """Get additive inverse of a real number.

    Parameters
    ----------
    input_number : float
        number for which additive inverse is required

    Returns
    -------
    NegativeResult
        negative of `input_number`

    Examples
    --------
    .. code-block:: pycon

        >>> from mcp_server.arithmetic_operations import get_negative
        >>> get_negative(1)
        NegativeResult(negative=-1.0)
        >>> get_negative(-1)
        NegativeResult(negative=1.0)
    """
    additive_inverse = InverseElements.ADDITIVE_INVERSE.value * input_number

    return NegativeResult(negative=additive_inverse)


class ReciprocalResult(pydantic.BaseModel):
    """Define result of reciprocal operation."""

    reciprocal: float


@pydantic.validate_call(validate_return=True)
def get_reciprocal(input_number: float) -> ReciprocalResult:
    """Get multiplicative inverse of a real number.

    Parameters
    ----------
    input_number : float
        number for which multiplicative inverse is required

    Returns
    -------
    ReciprocalResult
        reciprocal of `input_number`

    Raises
    ------
    DivisionByZeroError
        if `input_number` is additive identity, viz. zero

    Examples
    --------
    .. code-block:: pycon

        >>> from mcp_server.arithmetic_operations import get_reciprocal
        >>> get_reciprocal(2)
        ReciprocalResult(reciprocal=0.5)
        >>> get_reciprocal(0.5)
        ReciprocalResult(reciprocal=2.0)
    """
    if input_number == IdentityElements.ADDITIVE_IDENTITY.value:
        raise DivisionByZeroError

    multiplicative_inverse = InverseElements.MULTIPLICATIVE_INVERSE.value / input_number

    return ReciprocalResult(reciprocal=multiplicative_inverse)


__all__ = ["DivisionByZeroError", "InverseElements", "get_negative", "get_reciprocal"]
