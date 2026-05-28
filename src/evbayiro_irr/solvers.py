"""Comparison solvers for standard IRR root-finding methods."""

from __future__ import annotations

import math
from typing import List, Optional, Sequence

from .core import (
    DEFAULT_TOLERANCE,
    _npv_derivative_from_validated_cashflows,
    _npv_from_validated_cashflows,
    as_cashflow_tuple,
    signs_differ,
)
from .diagnostics import refine_bracket_bisection
from .results import IRRBracket, SolverResult, TrialPoint


def newton_irr(
    cashflows: Sequence[float],
    *,
    initial_guess: float = 0.10,
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = 100,
) -> SolverResult:
    """Find an IRR using Newton-Raphson from a chosen initial guess."""

    values = as_cashflow_tuple(cashflows)
    rate = float(initial_guess)
    path: List[TrialPoint] = []

    for iteration in range(1, max_iterations + 1):
        try:
            value = _npv_from_validated_cashflows(rate, values)
            derivative = _npv_derivative_from_validated_cashflows(rate, values)
        except ValueError:
            return SolverResult("newton", None, None, iteration, False, "invalid_rate", tuple(path))

        path.append(TrialPoint(rate, value))
        if abs(value) <= tolerance:
            return SolverResult("newton", rate, value, iteration, True, "converged", tuple(path))
        if derivative == 0 or not math.isfinite(derivative):
            return SolverResult("newton", None, None, iteration, False, "bad_derivative", tuple(path))

        next_rate = rate - value / derivative
        if next_rate <= -1 or not math.isfinite(next_rate):
            return SolverResult("newton", None, None, iteration, False, "invalid_rate", tuple(path))
        if abs(next_rate - rate) <= tolerance:
            final_npv = _npv_from_validated_cashflows(next_rate, values)
            return SolverResult("newton", next_rate, final_npv, iteration, True, "converged", tuple(path))
        rate = next_rate

    final_npv: Optional[float]
    try:
        final_npv = _npv_from_validated_cashflows(rate, values)
    except ValueError:
        final_npv = None
    return SolverResult("newton", rate, final_npv, max_iterations, False, "max_iterations", tuple(path))


def secant_irr(
    cashflows: Sequence[float],
    *,
    first_guess: float = 0.0,
    second_guess: float = 0.10,
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = 100,
) -> SolverResult:
    """Find an IRR using the secant method from two chosen guesses."""

    values = as_cashflow_tuple(cashflows)
    rate0 = float(first_guess)
    rate1 = float(second_guess)
    path: List[TrialPoint] = []

    try:
        value0 = _npv_from_validated_cashflows(rate0, values)
        value1 = _npv_from_validated_cashflows(rate1, values)
    except ValueError:
        return SolverResult("secant", None, None, 0, False, "invalid_rate", tuple(path))

    path.extend([TrialPoint(rate0, value0), TrialPoint(rate1, value1)])

    for iteration in range(1, max_iterations + 1):
        if abs(value1) <= tolerance:
            return SolverResult("secant", rate1, value1, iteration, True, "converged", tuple(path))
        denominator = value1 - value0
        if denominator == 0:
            return SolverResult("secant", None, None, iteration, False, "zero_denominator", tuple(path))

        next_rate = rate1 - value1 * (rate1 - rate0) / denominator
        if next_rate <= -1 or not math.isfinite(next_rate):
            return SolverResult("secant", None, None, iteration, False, "invalid_rate", tuple(path))

        next_value = _npv_from_validated_cashflows(next_rate, values)
        path.append(TrialPoint(next_rate, next_value))
        if abs(next_value) <= tolerance or abs(next_rate - rate1) <= tolerance:
            return SolverResult("secant", next_rate, next_value, iteration, True, "converged", tuple(path))

        rate0, value0 = rate1, value1
        rate1, value1 = next_rate, next_value

    return SolverResult("secant", rate1, value1, max_iterations, False, "max_iterations", tuple(path))


def bisection_irr(
    cashflows: Sequence[float],
    *,
    lower_rate: float,
    upper_rate: float,
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = 100,
) -> SolverResult:
    """Find an IRR inside a known sign-changing bracket."""

    values = as_cashflow_tuple(cashflows)
    lower_npv = _npv_from_validated_cashflows(lower_rate, values)
    upper_npv = _npv_from_validated_cashflows(upper_rate, values)
    path = [TrialPoint(lower_rate, lower_npv), TrialPoint(upper_rate, upper_npv)]

    if abs(lower_npv) <= tolerance:
        return SolverResult("bisection", lower_rate, lower_npv, len(path), True, "converged", tuple(path))
    if abs(upper_npv) <= tolerance:
        return SolverResult("bisection", upper_rate, upper_npv, len(path), True, "converged", tuple(path))
    if not signs_differ(lower_npv, upper_npv, tolerance=tolerance):
        return SolverResult("bisection", None, None, 0, False, "no_sign_change", tuple(path))

    bracket = IRRBracket(lower_rate, upper_rate, lower_npv, upper_npv)
    root = refine_bracket_bisection(
        values,
        bracket,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )
    root_npv = _npv_from_validated_cashflows(root, values)
    path.append(TrialPoint(root, root_npv))
    return SolverResult("bisection", root, root_npv, len(path), True, "converged", tuple(path))
