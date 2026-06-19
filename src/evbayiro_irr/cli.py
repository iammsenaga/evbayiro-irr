"""Command-line interface for Evbayiro-IRR."""

from __future__ import annotations

import argparse
import json
from typing import Iterable, List, Optional, Sequence

from . import __version__
from .method import evbayiro_analysis
from .results import EvbayiroResult, IRRBracket, TrialPoint


def parse_number(value: str) -> float:
    """Parse a CLI number, allowing comma and underscore separators."""

    cleaned = value.strip().replace(",", "").replace("_", "")
    if not cleaned:
        raise argparse.ArgumentTypeError("empty numeric value")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid number: {value!r}") from exc


def parse_rate(value: str) -> float:
    """Parse a CLI rate.

    Accepted forms:
    - 0.15 for 15%
    - 15% for 15%
    - 15 for 15%, as a finance-friendly shorthand
    """

    text = value.strip()
    if not text:
        raise argparse.ArgumentTypeError("empty rate value")
    is_percent = text.endswith("%")
    if is_percent:
        text = text[:-1]
    parsed = parse_number(text)
    if is_percent or abs(parsed) > 1:
        parsed = parsed / 100.0
    if parsed <= -1:
        raise argparse.ArgumentTypeError("rate must be greater than -100%")
    return parsed


def format_rate(value: Optional[float]) -> str:
    """Format a decimal rate as a percentage."""

    if value is None:
        return "None"
    return f"{value:.6%}"


def format_money(value: Optional[float]) -> str:
    """Format a monetary value for reports."""

    if value is None:
        return "None"
    return f"{value:,.2f}"


def _format_bracket(bracket: Optional[IRRBracket]) -> str:
    if bracket is None:
        return "None"
    return (
        f"{format_rate(bracket.lower_rate)} to {format_rate(bracket.upper_rate)} "
        f"(NPV {format_money(bracket.lower_npv)} to {format_money(bracket.upper_npv)})"
    )


def _format_trial_path(points: Iterable[TrialPoint], *, show_all: bool) -> List[str]:
    path = list(points)
    if not path:
        return ["  None"]
    if show_all or len(path) <= 12:
        visible = path
        omitted = 0
    else:
        visible = path[:6] + path[-3:]
        omitted = len(path) - len(visible)

    lines = [f"  {format_rate(point.rate):>12} -> {format_money(point.npv):>15}" for point in visible]
    if omitted:
        lines.insert(6, f"  ... {omitted} intermediate trial rates omitted; use --show-path")
    return lines


def format_result(result: EvbayiroResult, *, show_path: bool = False) -> str:
    """Return a readable CLI report for an Evbayiro analysis result."""

    lines = [
        "Evbayiro-IRR Analysis",
        "=====================",
        f"Cash-flow type: {result.cashflow_type.value}",
        f"Sign changes: {result.sign_changes}",
        f"RRR supplied: {'yes' if result.rrr is not None else 'no'}",
        f"Anchor rate: {format_rate(result.anchor_rate)}",
        f"NPV at anchor: {format_money(result.anchor_npv)}",
        f"Decision: {result.decision.value}",
        f"Decision basis: {result.decision_basis}",
        f"Search direction: {result.search_direction.value}",
        "",
        "Anchored Evbayiro Result",
        "------------------------",
        f"Anchored bracket: {_format_bracket(result.bracket)}",
        f"Estimated IRR: {format_rate(result.estimated_irr)}",
        f"Decision-relevant IRR: {format_rate(result.decision_relevant_irr)}",
        f"Closure method: {result.closure_method}",
        f"Closure status: {result.closure_status or 'None'}",
        f"Closure iterations: {result.closure_iterations if result.closure_iterations is not None else 'None'}",
        f"Scaled zero-NPV residual: {result.closure_scaled_residual if result.closure_scaled_residual is not None else 'None'}",
    ]

    if result.detected_irrs:
        lines.extend(
            [
                "",
                "Detected IRR Boundaries",
                "-----------------------",
            ]
        )
        for index, root in enumerate(result.detected_irrs, start=1):
            marker = " (decision-relevant)" if root == result.decision_relevant_irr else ""
            lines.append(f"{index}. {format_rate(root)}{marker}")

    lines.extend(
        [
            "",
            "Trial Path",
            "----------",
            *_format_trial_path(result.trial_path, show_all=show_path),
        ]
    )

    if result.warnings:
        lines.extend(["", "Warnings", "--------"])
        lines.extend(f"- {warning}" for warning in result.warnings)

    return "\n".join(lines)


def result_to_dict(result: EvbayiroResult) -> dict:
    """Convert a result object to JSON-friendly values."""

    return {
        "cashflows": list(result.cashflows),
        "rrr": result.rrr,
        "anchor_rate": result.anchor_rate,
        "anchor_npv": result.anchor_npv,
        "decision": result.decision.value,
        "decision_basis": result.decision_basis,
        "cashflow_type": result.cashflow_type.value,
        "sign_changes": result.sign_changes,
        "search_direction": result.search_direction.value,
        "trial_path": [{"rate": point.rate, "npv": point.npv} for point in result.trial_path],
        "bracket": _bracket_to_dict(result.bracket),
        "estimated_irr": result.estimated_irr,
        "detected_brackets": [_bracket_to_dict(bracket) for bracket in result.detected_brackets],
        "detected_irrs": list(result.detected_irrs),
        "decision_relevant_bracket": _bracket_to_dict(result.decision_relevant_bracket),
        "decision_relevant_irr": result.decision_relevant_irr,
        "closure_method": result.closure_method,
        "closure_iterations": result.closure_iterations,
        "closure_status": result.closure_status,
        "closure_scaled_residual": result.closure_scaled_residual,
        "warnings": list(result.warnings),
    }


def _bracket_to_dict(bracket: Optional[IRRBracket]) -> Optional[dict]:
    if bracket is None:
        return None
    return {
        "lower_rate": bracket.lower_rate,
        "upper_rate": bracket.upper_rate,
        "lower_npv": bracket.lower_npv,
        "upper_npv": bracket.upper_npv,
        "interpolated_rate": bracket.interpolated_rate,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        prog="evbayiro-irr",
        description="Run Evbayiro RRR-First capital-budgeting analysis.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"evbayiro-irr {__version__}",
    )
    parser.add_argument(
        "--cashflows",
        nargs="+",
        type=parse_number,
        metavar="CF",
        help="Cash flows ordered by period. Example: --cashflows -1000000 800000 1000000",
    )
    parser.add_argument(
        "--rrr",
        type=parse_rate,
        help="Required Rate of Return. Accepts 0.15, 15%%, or 15.",
    )
    parser.add_argument(
        "--step",
        type=parse_rate,
        default=0.01,
        help="Search increment. Default: 1%%.",
    )
    parser.add_argument(
        "--profile-min-rate",
        type=parse_rate,
        default=-0.99,
        help="Compatibility option from earlier profile-scan releases; validated but not used by the E3C workflow.",
    )
    parser.add_argument(
        "--profile-max-rate",
        type=parse_rate,
        default=1.0,
        help="Compatibility option from earlier profile-scan releases; validated but not used by the E3C workflow.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=1000,
        help="Maximum anchored step movements. Default: 1000.",
    )
    parser.add_argument(
        "--closure-max-iterations",
        type=int,
        default=100,
        help="Maximum E3C closure iterations. Default: 100.",
    )
    parser.add_argument(
        "--show-path",
        action="store_true",
        help="Show the full trial path instead of a shortened path.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a text report.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cashflows:
        parser.error("--cashflows is required unless --version is used")
    result = evbayiro_analysis(
        args.cashflows,
        rrr=args.rrr,
        step=args.step,
        max_steps=args.max_steps,
        closure_max_iterations=args.closure_max_iterations,
        profile_min_rate=args.profile_min_rate,
        profile_max_rate=args.profile_max_rate,
    )
    if args.json:
        print(json.dumps(result_to_dict(result), indent=2, sort_keys=True))
    else:
        print(format_result(result, show_path=args.show_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
