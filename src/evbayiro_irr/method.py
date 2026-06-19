"""Implementation of the Evbayiro RRR-First Method."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .cashflows import classify_cashflows, count_sign_changes
from .core import (
    DEFAULT_STEP,
    DEFAULT_TOLERANCE,
    EVBAYIRO_CONSTANT,
    _npv_from_validated_cashflows,
    as_cashflow_tuple,
    sign,
    signs_differ,
    validate_rate,
    validate_step,
)
from .diagnostics import make_bracket
from .e3c import E3CResult, iterated_e3c
from .results import (
    CashflowType,
    Decision,
    EvbayiroResult,
    IRRBracket,
    SearchDirection,
    TrialPoint,
)


def _decision(anchor_npv: float, *, rrr_supplied: bool, tolerance: float) -> Tuple[Decision, str]:
    if not rrr_supplied:
        return Decision.NOT_EVALUATED, "provisional_anchor_no_rrr"
    anchor_sign = sign(anchor_npv, tolerance=tolerance)
    if anchor_sign > 0:
        return Decision.ACCEPT, "npv_at_rrr"
    if anchor_sign < 0:
        return Decision.REJECT, "npv_at_rrr"
    return Decision.BREAKEVEN, "npv_at_rrr"


def _search_direction(anchor_npv: float, *, tolerance: float) -> SearchDirection:
    anchor_sign = sign(anchor_npv, tolerance=tolerance)
    if anchor_sign > 0:
        return SearchDirection.UPWARD
    if anchor_sign < 0:
        return SearchDirection.DOWNWARD
    return SearchDirection.NONE


def _anchored_step_search(
    cashflows: Sequence[float],
    *,
    anchor_rate: float,
    anchor_npv: float,
    step: float,
    max_steps: int,
    tolerance: float,
) -> Tuple[Tuple[TrialPoint, ...], Optional[IRRBracket], Optional[str]]:
    direction = _search_direction(anchor_npv, tolerance=tolerance)
    path: List[TrialPoint] = [TrialPoint(anchor_rate, anchor_npv)]

    if direction is SearchDirection.NONE:
        return tuple(path), None, None

    movement = step if direction is SearchDirection.UPWARD else -step
    previous = path[0]

    for index in range(1, max_steps + 1):
        next_rate = anchor_rate + movement * index
        if next_rate <= -1:
            return tuple(path), None, "Search stopped because the next rate would be <= -100%."

        point = TrialPoint(round(next_rate, 12), _npv_from_validated_cashflows(next_rate, cashflows))
        path.append(point)

        if sign(point.npv, tolerance=tolerance) == 0:
            return tuple(path), make_bracket(previous, point), None
        if signs_differ(previous.npv, point.npv, tolerance=tolerance):
            return tuple(path), make_bracket(previous, point), None

        previous = point

    return tuple(path), None, "No sign-changing bracket was found within max_steps."


def _single_direction_step_search(
    cashflows: Sequence[float],
    *,
    anchor_rate: float,
    step: float,
    max_steps: int,
    upward: bool,
    tolerance: float,
) -> Tuple[Tuple[TrialPoint, ...], Optional[IRRBracket], Optional[str]]:
    movement = step if upward else -step
    path: List[TrialPoint] = [TrialPoint(anchor_rate, _npv_from_validated_cashflows(anchor_rate, cashflows))]
    previous = path[0]

    for index in range(1, max_steps + 1):
        next_rate = anchor_rate + movement * index
        if next_rate <= -1:
            return tuple(path), None, "Search stopped because the next rate would be <= -100%."

        point = TrialPoint(round(next_rate, 12), _npv_from_validated_cashflows(next_rate, cashflows))
        path.append(point)

        if sign(point.npv, tolerance=tolerance) == 0:
            return tuple(path), make_bracket(previous, point), None
        if signs_differ(previous.npv, point.npv, tolerance=tolerance):
            return tuple(path), make_bracket(previous, point), None

        previous = point

    return tuple(path), None, "No sign-changing bracket was found within max_steps."


def _anchor_contiguous_search(
    cashflows: Sequence[float],
    *,
    anchor_rate: float,
    step: float,
    max_steps: int,
    tolerance: float,
) -> Tuple[Tuple[TrialPoint, ...], Optional[IRRBracket], Optional[IRRBracket], Tuple[str, ...]]:
    upper_path, upper_bracket, upper_warning = _single_direction_step_search(
        cashflows,
        anchor_rate=anchor_rate,
        step=step,
        max_steps=max_steps,
        upward=True,
        tolerance=tolerance,
    )
    lower_path, lower_bracket, lower_warning = _single_direction_step_search(
        cashflows,
        anchor_rate=anchor_rate,
        step=step,
        max_steps=max_steps,
        upward=False,
        tolerance=tolerance,
    )

    path: List[TrialPoint] = []
    seen: set[float] = set()
    for point in upper_path + lower_path:
        if point.rate in seen:
            continue
        seen.add(point.rate)
        path.append(point)

    warnings: List[str] = []
    if upper_warning:
        warnings.append(f"Upper anchor-contiguous search: {upper_warning}")
    if lower_warning:
        warnings.append(f"Lower anchor-contiguous search: {lower_warning}")

    return tuple(path), lower_bracket, upper_bracket, tuple(warnings)


def _close_bracket(
    cashflows: Sequence[float],
    bracket: IRRBracket,
    *,
    tolerance: float,
    max_iterations: int,
) -> E3CResult:
    return iterated_e3c(cashflows, bracket, tolerance=tolerance, max_iterations=max_iterations)


def evbayiro_analysis(
    cashflows: Sequence[float],
    *,
    rrr: Optional[float] = None,
    step: float = DEFAULT_STEP,
    require_irr: bool = True,
    max_steps: int = 1000,
    closure_max_iterations: int = 100,
    profile_min_rate: float = -0.99,
    profile_max_rate: float = 1.0,
    tolerance: float = DEFAULT_TOLERANCE,
) -> EvbayiroResult:
    """Run the Evbayiro RRR-First analysis workflow.

    Rates are expressed as decimals: 0.12 means 12%.
    """

    values = as_cashflow_tuple(cashflows)
    delta = validate_step(step)
    if max_steps <= 0:
        raise ValueError("max_steps must be a positive integer")
    if closure_max_iterations <= 0:
        raise ValueError("closure_max_iterations must be a positive integer")
    # Kept for API compatibility with earlier profile-scan releases.
    profile_min = validate_rate(profile_min_rate, name="profile_min_rate")
    profile_max = validate_rate(profile_max_rate, name="profile_max_rate")
    if profile_min >= profile_max:
        raise ValueError("profile_min_rate must be lower than profile_max_rate")

    rrr_supplied = rrr is not None
    anchor_rate = validate_rate(rrr if rrr_supplied else EVBAYIRO_CONSTANT, name="rrr")
    anchor_npv = _npv_from_validated_cashflows(anchor_rate, values)
    sign_changes = count_sign_changes(values, tolerance=tolerance)
    cashflow_type = classify_cashflows(values, tolerance=tolerance)
    decision, decision_basis = _decision(anchor_npv, rrr_supplied=rrr_supplied, tolerance=tolerance)
    direction = _search_direction(anchor_npv, tolerance=tolerance)

    warnings: List[str] = []
    if not rrr_supplied:
        warnings.append(
            "No RRR was supplied; the Evbayiro Constant of 10% was used only as a provisional search anchor."
        )
    if cashflow_type is CashflowType.NO_IRR_PATTERN:
        warnings.append("Cash flows do not change sign; a standard IRR boundary may not exist.")
    if cashflow_type is CashflowType.NON_CONVENTIONAL:
        warnings.append(
            "Non-conventional cash flows detected; multiple IRRs may exist and NPV at the RRR remains the controlling decision test."
        )

    trial_path: Tuple[TrialPoint, ...] = (TrialPoint(anchor_rate, anchor_npv),)
    bracket: Optional[IRRBracket] = None
    estimated_irr: Optional[float] = None
    detected_brackets: Tuple[IRRBracket, ...] = ()
    detected_irrs: Tuple[float, ...] = ()
    decision_relevant_bracket: Optional[IRRBracket] = None
    decision_relevant_irr: Optional[float] = None
    closure_result: Optional[E3CResult] = None

    if require_irr and cashflow_type is not CashflowType.NO_IRR_PATTERN:
        if direction is SearchDirection.NONE:
            estimated_irr = anchor_rate
            decision_relevant_irr = anchor_rate
            closure_result = E3CResult(anchor_rate, anchor_npv, 0.0, 0, True, "anchor_exact_irr")
        elif cashflow_type is CashflowType.CONVENTIONAL:
            trial_path, bracket, search_warning = _anchored_step_search(
                values,
                anchor_rate=anchor_rate,
                anchor_npv=anchor_npv,
                step=delta,
                max_steps=max_steps,
                tolerance=tolerance,
            )
            if search_warning:
                warnings.append(search_warning)
            if bracket:
                closure_result = _close_bracket(
                    values,
                    bracket,
                    tolerance=tolerance,
                    max_iterations=closure_max_iterations,
                )
                estimated_irr = closure_result.rate
                decision_relevant_bracket = bracket
                decision_relevant_irr = closure_result.rate
                if not closure_result.converged:
                    warnings.append(f"E3C closure did not meet tolerance: {closure_result.status}.")
        else:
            trial_path, lower_bracket, upper_bracket, search_warnings = _anchor_contiguous_search(
                values,
                anchor_rate=anchor_rate,
                step=delta,
                max_steps=max_steps,
                tolerance=tolerance,
            )
            detected = [bracket for bracket in (lower_bracket, upper_bracket) if bracket is not None]
            detected_brackets = tuple(detected)
            closure_by_bracket: dict[IRRBracket, E3CResult] = {}
            for detected_bracket in detected_brackets:
                result = _close_bracket(
                    values,
                    detected_bracket,
                    tolerance=tolerance,
                    max_iterations=closure_max_iterations,
                )
                closure_by_bracket[detected_bracket] = result
            detected_irrs = tuple(
                result.rate
                for result in (closure_by_bracket[detected] for detected in detected_brackets)
                if result.rate is not None
            )

            if anchor_npv >= 0 and upper_bracket is not None:
                decision_relevant_bracket = upper_bracket
            elif anchor_npv >= 0 and lower_bracket is not None:
                decision_relevant_bracket = lower_bracket
            elif lower_bracket is not None and upper_bracket is not None:
                decision_relevant_bracket = min(
                    (lower_bracket, upper_bracket),
                    key=lambda item: min(abs(anchor_rate - item.lower_rate), abs(anchor_rate - item.upper_rate)),
                )
            else:
                decision_relevant_bracket = lower_bracket or upper_bracket

            if decision_relevant_bracket is not None:
                bracket = decision_relevant_bracket
                closure_result = closure_by_bracket[decision_relevant_bracket]
                estimated_irr = closure_result.rate
                decision_relevant_irr = closure_result.rate
                if not closure_result.converged:
                    warnings.append(f"E3C closure did not meet tolerance: {closure_result.status}.")
            else:
                warnings.extend(search_warnings)

            if len(detected_brackets) > 1:
                warnings.append(
                    "More than one anchor-contiguous IRR boundary was detected; report the lower and upper RRR-region boundaries separately."
                )

    return EvbayiroResult(
        cashflows=values,
        rrr=rrr,
        anchor_rate=anchor_rate,
        anchor_npv=anchor_npv,
        decision=decision,
        decision_basis=decision_basis,
        cashflow_type=cashflow_type,
        sign_changes=sign_changes,
        search_direction=direction,
        trial_path=trial_path,
        bracket=bracket,
        estimated_irr=estimated_irr,
        detected_brackets=detected_brackets,
        detected_irrs=detected_irrs,
        decision_relevant_bracket=decision_relevant_bracket,
        decision_relevant_irr=decision_relevant_irr,
        warnings=tuple(warnings),
        closure_method="iterated_e3c",
        closure_iterations=closure_result.iterations if closure_result is not None else None,
        closure_status=closure_result.status if closure_result is not None else None,
        closure_scaled_residual=closure_result.scaled_residual if closure_result is not None else None,
    )
