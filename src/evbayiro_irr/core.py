"""Core financial math utilities."""

from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

EVBAYIRO_CONSTANT = 0.10
DEFAULT_STEP = 0.01
DEFAULT_TOLERANCE = 1e-9


def as_cashflow_tuple(cashflows: Iterable[float]) -> Tuple[float, ...]:
    """Validate and return cash flows as a tuple of floats."""

    values = tuple(float(value) for value in cashflows)
    if len(values) < 2:
        raise ValueError("cashflows must contain at least two values")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("cashflows must contain only finite numeric values")
    if all(value == 0 for value in values):
        raise ValueError("cashflows cannot all be zero")
    return values


def validate_rate(rate: float, *, name: str = "rate") -> float:
    """Validate a discount rate expressed as a decimal."""

    value = float(rate)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if value <= -1:
        raise ValueError(f"{name} must be greater than -1.0")
    return value


def validate_step(step: float) -> float:
    """Validate a positive rate step."""

    value = float(step)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("step must be a positive finite number")
    return value


def npv(rate: float, cashflows: Sequence[float]) -> float:
    """Return the net present value for a cash-flow sequence."""

    values = as_cashflow_tuple(cashflows)
    return _npv_from_validated_cashflows(rate, values)


def npv_derivative(rate: float, cashflows: Sequence[float]) -> float:
    """Return the derivative of NPV with respect to the discount rate."""

    values = as_cashflow_tuple(cashflows)
    return _npv_derivative_from_validated_cashflows(rate, values)


def _npv_from_validated_cashflows(rate: float, cashflows: Sequence[float]) -> float:
    """Return NPV for cash flows that have already been validated."""

    r = validate_rate(rate)
    discount_base = 1.0 + r
    discount_factor = 1.0
    total = 0.0
    for cashflow in cashflows:
        total += cashflow / discount_factor
        discount_factor *= discount_base
    return total


def _npv_derivative_from_validated_cashflows(rate: float, cashflows: Sequence[float]) -> float:
    """Return NPV derivative for cash flows that have already been validated."""

    r = validate_rate(rate)
    discount_base = 1.0 + r
    discount_factor = discount_base * discount_base
    total = 0.0
    for period, cashflow in enumerate(cashflows[1:], start=1):
        total -= period * cashflow / discount_factor
        discount_factor *= discount_base
    return total


def sign(value: float, *, tolerance: float = DEFAULT_TOLERANCE) -> int:
    """Return -1, 0, or 1 after applying a numerical tolerance."""

    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


def signs_differ(left: float, right: float, *, tolerance: float = DEFAULT_TOLERANCE) -> bool:
    """Return True when two values have opposite non-zero signs."""

    left_sign = sign(left, tolerance=tolerance)
    right_sign = sign(right, tolerance=tolerance)
    return left_sign != 0 and right_sign != 0 and left_sign != right_sign


def linear_interpolate_root(
    rate_a: float,
    value_a: float,
    rate_b: float,
    value_b: float,
) -> float:
    """Linearly estimate a zero crossing between two tested rates."""

    a = validate_rate(rate_a, name="rate_a")
    b = validate_rate(rate_b, name="rate_b")
    if value_a == value_b:
        raise ValueError("cannot interpolate when endpoint NPVs are equal")
    return a - value_a * (b - a) / (value_b - value_a)
