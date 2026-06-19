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


def brent_irr(
    cashflows: Sequence[float],
    *,
    lower_rate: float,
    upper_rate: float,
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = 100,
) -> SolverResult:
    """Find an IRR inside a known sign-changing bracket using Brent's method."""

    values = as_cashflow_tuple(cashflows)
    a = float(lower_rate)
    b = float(upper_rate)
    fa = _npv_from_validated_cashflows(a, values)
    fb = _npv_from_validated_cashflows(b, values)
    path = [TrialPoint(a, fa), TrialPoint(b, fb)]

    if abs(fa) <= tolerance:
        return SolverResult("brent", a, fa, len(path), True, "converged", tuple(path))
    if abs(fb) <= tolerance:
        return SolverResult("brent", b, fb, len(path), True, "converged", tuple(path))
    if not signs_differ(fa, fb, tolerance=tolerance):
        return SolverResult("brent", None, None, 0, False, "no_sign_change", tuple(path))

    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa

    c = a
    fc = fa
    d = e = b - a

    for iteration in range(1, max_iterations + 1):
        if fb == 0 or abs(b - a) <= tolerance:
            return SolverResult("brent", b, fb, iteration, True, "converged", tuple(path))

        if fa != fc and fb != fc:
            # Inverse quadratic interpolation.
            s = (
                a * fb * fc / ((fa - fb) * (fa - fc))
                + b * fa * fc / ((fb - fa) * (fb - fc))
                + c * fa * fb / ((fc - fa) * (fc - fb))
            )
        else:
            # Secant step.
            s = b - fb * (b - a) / (fb - fa)

        midpoint = (3 * a + b) / 4
        interpolation_ok = (
            min(midpoint, b) < s < max(midpoint, b)
            and abs(s - b) < abs(e) / 2
            and abs(e) > tolerance
        )
        if not interpolation_ok:
            s = (a + b) / 2
            e = d = b - a
        else:
            e = d
            d = b - s

        try:
            fs = _npv_from_validated_cashflows(s, values)
        except ValueError:
            return SolverResult("brent", None, None, iteration, False, "invalid_rate", tuple(path))
        path.append(TrialPoint(s, fs))

        c = a
        fc = fa
        if signs_differ(fa, fs, tolerance=tolerance):
            b = s
            fb = fs
        else:
            a = s
            fa = fs

        if abs(fa) < abs(fb):
            a, b = b, a
            fa, fb = fb, fa

        if abs(fb) <= tolerance:
            return SolverResult("brent", b, fb, iteration, True, "converged", tuple(path))

    return SolverResult("brent", b, fb, max_iterations, False, "max_iterations", tuple(path))
