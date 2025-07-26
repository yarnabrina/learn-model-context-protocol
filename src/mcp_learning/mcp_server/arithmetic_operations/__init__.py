"""Define arithmetic operations and their properties."""

from .axioms import (
    AdditionResult,
    DivisionByZeroError,
    IdentityElements,
    InverseElements,
    MultiplicationResult,
    NegativeResult,
    ReciprocalResult,
    add_numbers,
    get_negative,
    get_reciprocal,
    multiply_numbers,
)
from .derived_operations import DivisionResult, SubtractionResult, divide_numbers, subtract_numbers

__all__ = [
    "AdditionResult",
    "DivisionByZeroError",
    "DivisionResult",
    "IdentityElements",
    "InverseElements",
    "MultiplicationResult",
    "NegativeResult",
    "ReciprocalResult",
    "SubtractionResult",
    "add_numbers",
    "divide_numbers",
    "get_negative",
    "get_reciprocal",
    "multiply_numbers",
    "subtract_numbers",
]
