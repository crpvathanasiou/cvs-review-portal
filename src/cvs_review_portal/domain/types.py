"""Reusable strict scalar validators for portal contracts."""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import BeforeValidator


def parse_binary_label(value: object) -> Literal[0, 1]:
    """Accept only Python ints 0 or 1 (reject bool, float, str, other ints)."""
    if type(value) is not int:
        raise ValueError("binary label must be the integer 0 or 1")
    if value not in (0, 1):
        raise ValueError("binary label must be the integer 0 or 1")
    return value  # type: ignore[return-value]


def parse_nonnegative_int(value: object) -> int:
    """Accept only Python ints >= 0 (reject bool and floats)."""
    if type(value) is not int:
        raise ValueError("value must be a nonnegative integer")
    if value < 0:
        raise ValueError("value must be a nonnegative integer")
    return value


def parse_positive_int(value: object) -> int:
    """Accept only Python ints >= 1 (reject bool and floats)."""
    if type(value) is not int:
        raise ValueError("value must be a positive integer")
    if value < 1:
        raise ValueError("value must be a positive integer")
    return value


def parse_optional_unit_interval(value: object) -> float | None:
    """Accept null or a finite numeric value in [0, 1]; reject bool/NaN/inf/strings."""
    if value is None:
        return None
    if type(value) is bool:
        raise ValueError("metric score must be a finite number in [0, 1] or null")
    if type(value) is int:
        number = float(value)
    elif type(value) is float:
        number = value
    else:
        raise ValueError("metric score must be a finite number in [0, 1] or null")
    if math.isnan(number) or math.isinf(number):
        raise ValueError("metric score must be a finite number in [0, 1] or null")
    if number < 0.0 or number > 1.0:
        raise ValueError("metric score must be a finite number in [0, 1] or null")
    return number


def parse_optional_binary_label(value: object) -> Literal[0, 1] | None:
    """Accept null or a strict binary label."""
    if value is None:
        return None
    return parse_binary_label(value)


BinaryLabel = Annotated[Literal[0, 1], BeforeValidator(parse_binary_label)]
OptionalBinaryLabel = Annotated[Literal[0, 1] | None, BeforeValidator(parse_optional_binary_label)]
NonNegativeInt = Annotated[int, BeforeValidator(parse_nonnegative_int)]
PositiveInt = Annotated[int, BeforeValidator(parse_positive_int)]
OptionalUnitInterval = Annotated[float | None, BeforeValidator(parse_optional_unit_interval)]
