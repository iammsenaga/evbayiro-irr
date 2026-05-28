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
from .diagnostics import (
    choose_decision_relevant_bracket,
    make_bracket,
    refine_bracket_bisection,
    scan_npv_profile,
)
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


def evbayiro_analysis(
    cashflows: Sequence[float],
    *,
    rrr: Optional[float] = None,
    step: float = DEFAULT_STEP,
    require_irr: bool = True,
    max_steps: int = 1000,
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

    if require_irr and cashflow_type is not CashflowType.NO_IRR_PATTERN:
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
            estimated_irr = bracket.interpolated_rate
        elif direction is SearchDirection.NONE:
            estimated_irr = anchor_rate

    detected_brackets: Tuple[IRRBracket, ...] = ()
    detected_irrs: Tuple[float, ...] = ()
    decision_relevant_bracket: Optional[IRRBracket] = bracket
    decision_relevant_irr: Optional[float] = estimated_irr

    if cashflow_type is CashflowType.NON_CONVENTIONAL:
        _, detected_brackets = scan_npv_profile(
            values,
            min_rate=profile_min_rate,
            max_rate=profile_max_rate,
            step=delta,
            tolerance=tolerance,
        )
        detected_irrs = tuple(
            refine_bracket_bisection(values, detected, tolerance=tolerance)
            for detected in detected_brackets
        )
        chosen = choose_decision_relevant_bracket(
            detected_brackets,
            anchor_rate=anchor_rate,
            anchor_npv=anchor_npv,
        )
        if chosen is not None:
            decision_relevant_bracket = chosen
            decision_relevant_irr = refine_bracket_bisection(values, chosen, tolerance=tolerance)
        if len(detected_brackets) > 1:
            warnings.append(
                "More than one IRR boundary was detected; report all roots and label the RRR-region boundary separately."
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
    )
