"""Diagnostic NPV profile scanning."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

from .core import (
    DEFAULT_STEP,
    DEFAULT_TOLERANCE,
    _npv_from_validated_cashflows,
    as_cashflow_tuple,
    signs_differ,
    validate_rate,
    validate_step,
)
from .results import IRRBracket, TrialPoint


def make_bracket(left: TrialPoint, right: TrialPoint) -> IRRBracket:
    """Create a rate-sorted IRR bracket from two trial points."""

    if left.rate <= right.rate:
        return IRRBracket(left.rate, right.rate, left.npv, right.npv)
    return IRRBracket(right.rate, left.rate, right.npv, left.npv)


def scan_npv_profile(
    cashflows: Sequence[float],
    *,
    min_rate: float = -0.99,
    max_rate: float = 1.0,
    step: float = DEFAULT_STEP,
    tolerance: float = DEFAULT_TOLERANCE,
) -> Tuple[Tuple[TrialPoint, ...], Tuple[IRRBracket, ...]]:
    """Scan a rate range and return tested points plus sign-change brackets."""

    values = as_cashflow_tuple(cashflows)
    lower = validate_rate(min_rate, name="min_rate")
    upper = validate_rate(max_rate, name="max_rate")
    delta = validate_step(step)
    if lower >= upper:
        raise ValueError("min_rate must be lower than max_rate")

    points: List[TrialPoint] = []
    brackets: List[IRRBracket] = []
    rate = lower

    while rate <= upper + (delta * 1e-9):
        rounded_rate = round(rate, 12)
        point = TrialPoint(rounded_rate, _npv_from_validated_cashflows(rounded_rate, values))
        if points:
            previous = points[-1]
            if signs_differ(previous.npv, point.npv, tolerance=tolerance):
                brackets.append(make_bracket(previous, point))
        points.append(point)
        rate += delta

    if points[-1].rate < upper:
        point = TrialPoint(upper, _npv_from_validated_cashflows(upper, values))
        previous = points[-1]
        if signs_differ(previous.npv, point.npv, tolerance=tolerance):
            brackets.append(make_bracket(previous, point))
        points.append(point)

    return tuple(points), tuple(brackets)


def refine_bracket_bisection(
    cashflows: Sequence[float],
    bracket: IRRBracket,
    *,
    tolerance: float = 1e-12,
    max_iterations: int = 100,
) -> float:
    """Refine a sign-changing bracket using bisection."""

    values = as_cashflow_tuple(cashflows)
    low_rate = bracket.lower_rate
    high_rate = bracket.upper_rate
    low_npv = bracket.lower_npv
    high_npv = bracket.upper_npv

    if not signs_differ(low_npv, high_npv, tolerance=tolerance):
        return bracket.interpolated_rate

    for _ in range(max_iterations):
        mid_rate = (low_rate + high_rate) / 2.0
        mid_npv = _npv_from_validated_cashflows(mid_rate, values)
        if abs(mid_npv) <= tolerance or abs(high_rate - low_rate) <= tolerance:
            return mid_rate
        if signs_differ(low_npv, mid_npv, tolerance=tolerance):
            high_rate = mid_rate
            high_npv = mid_npv
        else:
            low_rate = mid_rate
            low_npv = mid_npv

    return (low_rate + high_rate) / 2.0


def choose_decision_relevant_bracket(
    brackets: Iterable[IRRBracket],
    *,
    anchor_rate: float,
    anchor_npv: float,
) -> Optional[IRRBracket]:
    """Choose the IRR boundary most relevant to the RRR region."""

    ordered = sorted(brackets, key=lambda bracket: bracket.lower_rate)
    if not ordered:
        return None

    if anchor_npv >= 0:
        for bracket in ordered:
            if bracket.upper_rate >= anchor_rate and not bracket.contains_rate(anchor_rate):
                return bracket
        for bracket in ordered:
            if bracket.contains_rate(anchor_rate):
                return bracket
        lower_brackets = [bracket for bracket in ordered if bracket.upper_rate < anchor_rate]
        return lower_brackets[-1] if lower_brackets else None

    containing = [bracket for bracket in ordered if bracket.contains_rate(anchor_rate)]
    if containing:
        return containing[0]

    return min(
        ordered,
        key=lambda bracket: min(
            abs(anchor_rate - bracket.lower_rate),
            abs(anchor_rate - bracket.upper_rate),
        ),
    )
