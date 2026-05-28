"""Cash-flow classification helpers."""

from __future__ import annotations

from typing import Iterable, Tuple

from .core import DEFAULT_TOLERANCE, as_cashflow_tuple
from .results import CashflowType


def cashflow_signs(
    cashflows: Iterable[float],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> Tuple[int, ...]:
    """Return cash-flow signs while ignoring economically zero cash flows."""

    signs = []
    for value in as_cashflow_tuple(cashflows):
        if value > tolerance:
            signs.append(1)
        elif value < -tolerance:
            signs.append(-1)
    return tuple(signs)


def count_sign_changes(
    cashflows: Iterable[float],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> int:
    """Count sign changes after ignoring zero cash flows."""

    signs = cashflow_signs(cashflows, tolerance=tolerance)
    return sum(1 for left, right in zip(signs, signs[1:]) if left != right)


def classify_cashflows(
    cashflows: Iterable[float],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> CashflowType:
    """Classify cash flows as conventional, non-conventional, or no-IRR."""

    changes = count_sign_changes(cashflows, tolerance=tolerance)
    if changes == 1:
        return CashflowType.CONVENTIONAL
    if changes > 1:
        return CashflowType.NON_CONVENTIONAL
    return CashflowType.NO_IRR_PATTERN

