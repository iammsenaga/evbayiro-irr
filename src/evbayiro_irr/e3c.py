"""Evbayiro Three-Point Curvature Closure (E3C)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

from .core import DEFAULT_TOLERANCE, _npv_from_validated_cashflows, sign
from .results import IRRBracket


@dataclass(frozen=True)
class E3CResult:
    """Result of one-step or iterated E3C closure."""

    rate: Optional[float]
    npv_at_rate: Optional[float]
    scaled_residual: Optional[float]
    iterations: int
    converged: bool
    status: str


def cashflow_scale(cashflows: Sequence[float]) -> float:
    """Return the E3C residual denominator, sum(|CF_t|)."""

    return sum(abs(value) for value in cashflows)


def scaled_zero_npv_residual(cashflows: Sequence[float], npv_value: Optional[float]) -> Optional[float]:
    """Return R(r) = |NPV(r)| / sum(|CF_t|)."""

    if npv_value is None:
        return None
    scale = cashflow_scale(cashflows)
    if scale == 0:
        return None
    return abs(npv_value) / scale


def signs_differ_or_zero(left: float, right: float, *, tolerance: float = DEFAULT_TOLERANCE) -> bool:
    """Return True when two NPVs create an adjacent E3C bracket."""

    left_sign = sign(left, tolerance=tolerance)
    right_sign = sign(right, tolerance=tolerance)
    return left_sign == 0 or right_sign == 0 or left_sign != right_sign


def e3c_close_once(
    cashflows: Sequence[float],
    bracket: IRRBracket,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> E3CResult:
    """Close one Evbayiro bracket using the E3C formula."""

    r_l = bracket.lower_rate
    r_u = bracket.upper_rate
    if r_u < r_l:
        return E3CResult(None, None, None, 0, False, "invalid_bracket")
    if r_u == r_l:
        residual = scaled_zero_npv_residual(cashflows, bracket.lower_npv)
        return E3CResult(r_l, bracket.lower_npv, residual, 0, residual is not None and residual <= tolerance, "exact_anchor")

    n_l = bracket.lower_npv
    n_u = bracket.upper_npv
    if sign(n_l, tolerance=tolerance) == 0:
        residual = scaled_zero_npv_residual(cashflows, n_l)
        return E3CResult(r_l, n_l, residual, 1, True, "lower_endpoint_exact")
    if sign(n_u, tolerance=tolerance) == 0:
        residual = scaled_zero_npv_residual(cashflows, n_u)
        return E3CResult(r_u, n_u, residual, 1, True, "upper_endpoint_exact")

    r_m = (r_l + r_u) / 2.0
    n_m = _npv_from_validated_cashflows(r_m, cashflows)

    coefficient_a = 2.0 * (n_l + n_u - 2.0 * n_m)
    coefficient_b = 4.0 * n_m - 3.0 * n_l - n_u
    coefficient_c = n_l

    candidates: list[tuple[float, float, float, str]] = []
    if coefficient_a == 0.0:
        if coefficient_b == 0.0:
            return E3CResult(None, None, None, 1, False, "no_linear_limiting_solution")
        x_value = -coefficient_c / coefficient_b
        if math.isfinite(x_value) and 0.0 <= x_value <= 1.0:
            rate = r_l + x_value * (r_u - r_l)
            npv_value = _npv_from_validated_cashflows(rate, cashflows)
            residual = scaled_zero_npv_residual(cashflows, npv_value)
            return E3CResult(
                rate,
                npv_value,
                residual,
                1,
                residual is not None and residual <= tolerance,
                "linear_limiting_form",
            )
        return E3CResult(None, None, None, 1, False, "linear_limiting_root_outside_bracket")

    discriminant = coefficient_b * coefficient_b - 4.0 * coefficient_a * coefficient_c
    if discriminant < 0.0:
        return E3CResult(None, None, None, 1, False, "no_real_e3c_root")

    square_root = math.sqrt(discriminant)
    for x_value in (
        (-coefficient_b - square_root) / (2.0 * coefficient_a),
        (-coefficient_b + square_root) / (2.0 * coefficient_a),
    ):
        if math.isfinite(x_value) and 0.0 <= x_value <= 1.0:
            rate = r_l + x_value * (r_u - r_l)
            npv_value = _npv_from_validated_cashflows(rate, cashflows)
            candidates.append((abs(npv_value), rate, npv_value, "quadratic_root"))

    if not candidates:
        return E3CResult(None, None, None, 1, False, "no_in_bracket_e3c_root")

    _, rate, npv_value, status = min(candidates, key=lambda item: item[0])
    if len(candidates) > 1:
        status = "two_in_bracket_roots_choose_smaller_residual"
    residual = scaled_zero_npv_residual(cashflows, npv_value)
    return E3CResult(rate, npv_value, residual, 1, residual is not None and residual <= tolerance, status)


def iterated_e3c(
    cashflows: Sequence[float],
    bracket: IRRBracket,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = 100,
) -> E3CResult:
    """Repeat E3C closure until the scaled zero-NPV residual is within tolerance."""

    if max_iterations <= 0:
        raise ValueError("max_iterations must be a positive integer")

    r_l = bracket.lower_rate
    r_u = bracket.upper_rate
    n_l = bracket.lower_npv
    n_u = bracket.upper_npv
    last: Optional[E3CResult] = None

    if not signs_differ_or_zero(n_l, n_u, tolerance=tolerance):
        return E3CResult(None, None, None, 0, False, "initial_bracket_has_no_adjacent_sign_change")

    for iteration in range(1, max_iterations + 1):
        step = e3c_close_once(
            cashflows,
            IRRBracket(r_l, r_u, n_l, n_u),
            tolerance=tolerance,
        )
        last = E3CResult(
            step.rate,
            step.npv_at_rate,
            step.scaled_residual,
            iteration,
            step.converged,
            step.status,
        )
        if step.rate is None or step.npv_at_rate is None:
            return last
        if step.scaled_residual is not None and step.scaled_residual <= tolerance:
            return E3CResult(step.rate, step.npv_at_rate, step.scaled_residual, iteration, True, "solved")

        if signs_differ_or_zero(n_l, step.npv_at_rate, tolerance=tolerance):
            r_u = step.rate
            n_u = step.npv_at_rate
        elif signs_differ_or_zero(step.npv_at_rate, n_u, tolerance=tolerance):
            r_l = step.rate
            n_l = step.npv_at_rate
        else:
            return E3CResult(
                step.rate,
                step.npv_at_rate,
                step.scaled_residual,
                iteration,
                False,
                "cannot_preserve_adjacent_sign_change",
            )

    if last is None:
        return E3CResult(None, None, None, 0, False, "not_started")
    return E3CResult(last.rate, last.npv_at_rate, last.scaled_residual, max_iterations, False, "max_iterations")
