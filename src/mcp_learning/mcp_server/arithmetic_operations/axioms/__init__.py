"""Define axiomatic arithmetic operations and their properties."""

from .fundamental_operations import (
    AdditionResult,
    IdentityElements,
    MultiplicationResult,
    add_numbers,
    multiply_numbers,
)
from .inverses import (
    DivisionByZeroError,
    InverseElements,
    NegativeResult,
    ReciprocalResult,
    get_negative,
    get_reciprocal,
)

__all__ = [
    "AdditionResult",
    "DivisionByZeroError",
    "IdentityElements",
    "InverseElements",
    "MultiplicationResult",
    "NegativeResult",
    "ReciprocalResult",
    "add_numbers",
    "get_negative",
    "get_reciprocal",
    "multiply_numbers",
]
