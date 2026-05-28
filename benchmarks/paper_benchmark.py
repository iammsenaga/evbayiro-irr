"""Generate local benchmark data for Evbayiro-IRR paper analysis."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
BENCHMARK_DEPS = ROOT / ".benchmark_deps"
if BENCHMARK_DEPS.exists() and str(BENCHMARK_DEPS) not in sys.path:
    sys.path.insert(0, str(BENCHMARK_DEPS))

try:
    import numpy_financial as npf
except ImportError:  # pragma: no cover - optional benchmark dependency
    npf = None

try:
    import pyxirr
except ImportError:  # pragma: no cover - optional benchmark dependency
    pyxirr = None

from evbayiro_irr import bisection_irr, evbayiro_analysis, newton_irr, secant_irr
from evbayiro_irr.cashflows import classify_cashflows
from evbayiro_irr.core import npv
from evbayiro_irr.diagnostics import scan_npv_profile
from evbayiro_irr.examples import (
    manuscript_example_2,
    manuscript_non_conventional_example,
)
from evbayiro_irr.results import CashflowType, EvbayiroResult

BENCHMARK_EVBAYIRO_MAX_STEPS = 5000


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    case_type: str
    cashflows: tuple[float, ...]
    rrr: float


def timed(callback: Callable[[], object]) -> tuple[object, float]:
    start = perf_counter()
    result = callback()
    return result, perf_counter() - start


def fmt_float(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{value:.12g}"


def root_relation(root: Optional[float], evbayiro_result: EvbayiroResult) -> str:
    if root is None:
        return "none"
    if evbayiro_result.decision_relevant_irr is None:
        return "not_applicable"
    if abs(root - evbayiro_result.decision_relevant_irr) <= 1e-5:
        return "decision_relevant"
    if (
        evbayiro_result.decision_relevant_bracket is not None
        and evbayiro_result.decision_relevant_bracket.contains_rate(root)
    ):
        return "decision_relevant"
    return "other_root"


def method_decision(root: Optional[float], rrr: float) -> str:
    if root is None:
        return "not_available"
    if abs(root - rrr) <= 1e-9:
        return "breakeven"
    if root > rrr:
        return "accept"
    return "reject"


def decision_matches_npv(method_decision_value: str, npv_decision: str) -> str:
    if method_decision_value in {"not_available", "not_evaluated", "not_applicable"}:
        return "not_applicable"
    if npv_decision == "breakeven" and method_decision_value in {"accept", "breakeven"}:
        return "true"
    return "true" if method_decision_value == npv_decision else "false"


def root_error_bps(root: Optional[float], evbayiro_result: EvbayiroResult) -> str:
    if root is None or evbayiro_result.decision_relevant_irr is None:
        return ""
    return fmt_float(abs(root - evbayiro_result.decision_relevant_irr) * 10_000)


def npv_at_root(cashflows: Sequence[float], root: Optional[float]) -> str:
    if root is None:
        return ""
    try:
        return fmt_float(npv(root, cashflows))
    except ValueError:
        return ""


def finite_root(value: object) -> Optional[float]:
    try:
        root = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(root) or root <= -1:
        return None
    return root


def make_conventional_case(case_id: str, rng: random.Random) -> BenchmarkCase:
    initial_outflow = -rng.randint(5_000, 80_000)
    periods = rng.randint(3, 8)
    inflows = tuple(float(rng.randint(1_000, 25_000)) for _ in range(periods))
    rrr = rng.choice((0.08, 0.10, 0.12, 0.15, 0.20))
    return BenchmarkCase(case_id, "generated_conventional", (float(initial_outflow), *inflows), rrr)


def make_non_conventional_case(case_id: str, rng: random.Random) -> BenchmarkCase:
    initial_outflow = -rng.randint(50_000, 400_000)
    periods = rng.randint(3, 5)
    inflows = [float(rng.randint(30_000, 250_000)) for _ in range(periods)]
    terminal_outflow = -float(rng.randint(40_000, 450_000))
    rrr = rng.choice((0.08, 0.10, 0.12, 0.15, 0.20, 0.25))
    return BenchmarkCase(
        case_id,
        "generated_non_conventional",
        (float(initial_outflow), *inflows, terminal_outflow),
        rrr,
    )


def has_detectable_root(cashflows: Sequence[float]) -> bool:
    _, brackets = scan_npv_profile(cashflows, min_rate=-0.50, max_rate=1.0, step=0.01)
    return bool(brackets)


def generate_cases(per_type: int, seed: int) -> list[BenchmarkCase]:
    rng = random.Random(seed)
    cases = [
        BenchmarkCase("manuscript_conventional_2", "manuscript_conventional", manuscript_example_2(), 0.11),
        BenchmarkCase(
            "manuscript_non_conventional",
            "manuscript_non_conventional",
            manuscript_non_conventional_example(),
            0.15,
        ),
    ]

    conventional_count = 0
    attempts = 0
    while conventional_count < per_type and attempts < per_type * 30:
        attempts += 1
        case = make_conventional_case(f"generated_conventional_{conventional_count + 1:03d}", rng)
        if classify_cashflows(case.cashflows) is CashflowType.CONVENTIONAL and has_detectable_root(case.cashflows):
            cases.append(case)
            conventional_count += 1

    non_conventional_count = 0
    attempts = 0
    while non_conventional_count < per_type and attempts < per_type * 80:
        attempts += 1
        case = make_non_conventional_case(f"generated_non_conventional_{non_conventional_count + 1:03d}", rng)
        if classify_cashflows(case.cashflows) is CashflowType.NON_CONVENTIONAL and has_detectable_root(case.cashflows):
            cases.append(case)
            non_conventional_count += 1

    return cases


def base_row(case: BenchmarkCase, evbayiro_result) -> dict:
    return {
        "case_id": case.case_id,
        "case_type": case.case_type,
        "cashflow_type": evbayiro_result.cashflow_type.value,
        "period_count": len(case.cashflows) - 1,
        "rrr": fmt_float(case.rrr),
        "npv_at_rrr": fmt_float(evbayiro_result.anchor_npv),
        "decision": evbayiro_result.decision.value,
        "sign_changes": evbayiro_result.sign_changes,
        "detected_irr_count": len(evbayiro_result.detected_irrs),
        "multiple_irr_detected": len(evbayiro_result.detected_irrs) > 1,
        "detected_irrs": "|".join(fmt_float(root) for root in evbayiro_result.detected_irrs),
        "decision_relevant_irr": fmt_float(evbayiro_result.decision_relevant_irr),
        "rrr_to_decision_relevant_bps": root_error_bps(case.rrr, evbayiro_result),
    }


def benchmark_case(case: BenchmarkCase) -> list[dict]:
    rows: List[dict] = []
    evbayiro_result, elapsed = timed(
        lambda: evbayiro_analysis(
            case.cashflows,
            rrr=case.rrr,
            max_steps=BENCHMARK_EVBAYIRO_MAX_STEPS,
        )
    )
    row = base_row(case, evbayiro_result)
    evbayiro_root = evbayiro_result.decision_relevant_irr
    evbayiro_root_decision = method_decision(evbayiro_root, case.rrr)
    evbayiro_decision = evbayiro_result.decision.value
    row.update(
        {
            "method": "evbayiro_rrr_first",
            "decision_rule": evbayiro_result.decision_basis,
            "seed": "",
            "root": fmt_float(evbayiro_root),
            "npv_at_root": npv_at_root(case.cashflows, evbayiro_root),
            "root_error_to_relevant_bps": root_error_bps(evbayiro_root, evbayiro_result),
            "root_relation": "decision_relevant" if evbayiro_root is not None else "none",
            "method_decision_from_root": evbayiro_root_decision,
            "method_decision": evbayiro_decision,
            "decision_matches_npv": decision_matches_npv(evbayiro_decision, evbayiro_result.decision.value),
            "converged": evbayiro_root is not None,
            "status": "completed",
            "iterations_or_trials": len(evbayiro_result.trial_path),
            "time_seconds": f"{elapsed:.9f}",
        }
    )
    rows.append(row)

    for seed in (0.05, case.rrr, 0.30):
        solver_result, elapsed = timed(lambda seed=seed: newton_irr(case.cashflows, initial_guess=seed))
        row = base_row(case, evbayiro_result)
        solver_decision = method_decision(solver_result.root, case.rrr)
        row.update(
            {
                "method": "newton",
                "decision_rule": "root_vs_rrr",
                "seed": fmt_float(seed),
                "root": fmt_float(solver_result.root),
                "npv_at_root": npv_at_root(case.cashflows, solver_result.root),
                "root_error_to_relevant_bps": root_error_bps(solver_result.root, evbayiro_result),
                "root_relation": root_relation(solver_result.root, evbayiro_result),
                "method_decision_from_root": solver_decision,
                "method_decision": solver_decision,
                "decision_matches_npv": decision_matches_npv(solver_decision, evbayiro_result.decision.value),
                "converged": solver_result.converged,
                "status": solver_result.status,
                "iterations_or_trials": solver_result.iterations,
                "time_seconds": f"{elapsed:.9f}",
            }
        )
        rows.append(row)

    secant_pairs = ((0.0, 0.10), (case.rrr, case.rrr + 0.01), (0.20, 0.30))
    for first, second in secant_pairs:
        solver_result, elapsed = timed(
            lambda first=first, second=second: secant_irr(
                case.cashflows,
                first_guess=first,
                second_guess=second,
            )
        )
        row = base_row(case, evbayiro_result)
        solver_decision = method_decision(solver_result.root, case.rrr)
        row.update(
            {
                "method": "secant",
                "decision_rule": "root_vs_rrr",
                "seed": f"{fmt_float(first)}|{fmt_float(second)}",
                "root": fmt_float(solver_result.root),
                "npv_at_root": npv_at_root(case.cashflows, solver_result.root),
                "root_error_to_relevant_bps": root_error_bps(solver_result.root, evbayiro_result),
                "root_relation": root_relation(solver_result.root, evbayiro_result),
                "method_decision_from_root": solver_decision,
                "method_decision": solver_decision,
                "decision_matches_npv": decision_matches_npv(solver_decision, evbayiro_result.decision.value),
                "converged": solver_result.converged,
                "status": solver_result.status,
                "iterations_or_trials": solver_result.iterations,
                "time_seconds": f"{elapsed:.9f}",
            }
        )
        rows.append(row)

    solver_result, elapsed = timed(lambda: newton_irr(case.cashflows, initial_guess=0.10, max_iterations=20))
    row = base_row(case, evbayiro_result)
    solver_decision = method_decision(solver_result.root, case.rrr)
    row.update(
        {
            "method": "excel_default_guess_proxy",
            "decision_rule": "root_vs_rrr_default_guess_10pct_proxy",
            "seed": "0.1",
            "root": fmt_float(solver_result.root),
            "npv_at_root": npv_at_root(case.cashflows, solver_result.root),
            "root_error_to_relevant_bps": root_error_bps(solver_result.root, evbayiro_result),
            "root_relation": root_relation(solver_result.root, evbayiro_result),
            "method_decision_from_root": solver_decision,
            "method_decision": solver_decision,
            "decision_matches_npv": decision_matches_npv(solver_decision, evbayiro_result.decision.value),
            "converged": solver_result.converged,
            "status": solver_result.status,
            "iterations_or_trials": solver_result.iterations,
            "time_seconds": f"{elapsed:.9f}",
        }
    )
    rows.append(row)

    if npf is not None:
        def run_numpy_financial_irr() -> Optional[float]:
            return finite_root(npf.irr(case.cashflows))

        root, elapsed = timed(run_numpy_financial_irr)
        row = base_row(case, evbayiro_result)
        solver_decision = method_decision(root, case.rrr)
        row.update(
            {
                "method": "numpy_financial_irr",
                "decision_rule": "root_vs_rrr_scalar_finance_function",
                "seed": "",
                "root": fmt_float(root),
                "npv_at_root": npv_at_root(case.cashflows, root),
                "root_error_to_relevant_bps": root_error_bps(root, evbayiro_result),
                "root_relation": root_relation(root, evbayiro_result),
                "method_decision_from_root": solver_decision,
                "method_decision": solver_decision,
                "decision_matches_npv": decision_matches_npv(solver_decision, evbayiro_result.decision.value),
                "converged": root is not None,
                "status": "completed" if root is not None else "no_root_returned",
                "iterations_or_trials": 1,
                "time_seconds": f"{elapsed:.9f}",
            }
        )
        rows.append(row)

    if pyxirr is not None:
        def run_pyxirr_irr() -> Optional[float]:
            return finite_root(pyxirr.irr(case.cashflows))

        try:
            root, elapsed = timed(run_pyxirr_irr)
            status = "completed" if root is not None else "no_root_returned"
        except Exception as error:  # pyxirr raises on same-sign cash flows
            root = None
            elapsed = 0.0
            status = type(error).__name__
        row = base_row(case, evbayiro_result)
        solver_decision = method_decision(root, case.rrr)
        row.update(
            {
                "method": "pyxirr_irr",
                "decision_rule": "root_vs_rrr_library_multiple_irr_policy",
                "seed": "",
                "root": fmt_float(root),
                "npv_at_root": npv_at_root(case.cashflows, root),
                "root_error_to_relevant_bps": root_error_bps(root, evbayiro_result),
                "root_relation": root_relation(root, evbayiro_result),
                "method_decision_from_root": solver_decision,
                "method_decision": solver_decision,
                "decision_matches_npv": decision_matches_npv(solver_decision, evbayiro_result.decision.value),
                "converged": root is not None,
                "status": status,
                "iterations_or_trials": 1,
                "time_seconds": f"{elapsed:.9f}",
            }
        )
        rows.append(row)

    if evbayiro_result.decision_relevant_bracket is not None:
        bracket = evbayiro_result.decision_relevant_bracket
        solver_result, elapsed = timed(
            lambda: bisection_irr(
                case.cashflows,
                lower_rate=bracket.lower_rate,
                upper_rate=bracket.upper_rate,
            )
        )
        row = base_row(case, evbayiro_result)
        solver_root_decision = method_decision(solver_result.root, case.rrr)
        solver_decision = "not_evaluated"
        row.update(
            {
                "method": "bisection_known_bracket",
                "decision_rule": "known_bracket_control",
                "seed": f"{fmt_float(bracket.lower_rate)}|{fmt_float(bracket.upper_rate)}",
                "root": fmt_float(solver_result.root),
                "npv_at_root": npv_at_root(case.cashflows, solver_result.root),
                "root_error_to_relevant_bps": root_error_bps(solver_result.root, evbayiro_result),
                "root_relation": root_relation(solver_result.root, evbayiro_result),
                "method_decision_from_root": solver_root_decision,
                "method_decision": solver_decision,
                "decision_matches_npv": decision_matches_npv(solver_decision, evbayiro_result.decision.value),
                "converged": solver_result.converged,
                "status": solver_result.status,
                "iterations_or_trials": solver_result.iterations,
                "time_seconds": f"{elapsed:.9f}",
            }
        )
        rows.append(row)

    return rows


def summarize(rows: Iterable[dict]) -> list[dict]:
    rows = list(rows)
    by_method: dict[str, dict[str, float]] = {}
    for row in rows:
        method = row["method"]
        stats = by_method.setdefault(
            method,
            {
                "rows": 0,
                "converged": 0,
                "other_root": 0,
                "decision_evaluated": 0,
                "decision_mismatch": 0,
                "root_error_bps_total": 0.0,
                "root_error_bps_count": 0,
                "iterations_or_trials_total": 0.0,
                "time_seconds_total": 0.0,
            },
        )
        stats["rows"] += 1
        if str(row["converged"]) == "True":
            stats["converged"] += 1
        if row["root_relation"] == "other_root":
            stats["other_root"] += 1
        if row["decision_matches_npv"] in {"true", "false"}:
            stats["decision_evaluated"] += 1
            if row["decision_matches_npv"] == "false":
                stats["decision_mismatch"] += 1
        if row["root_error_to_relevant_bps"]:
            stats["root_error_bps_total"] += float(row["root_error_to_relevant_bps"])
            stats["root_error_bps_count"] += 1
        stats["iterations_or_trials_total"] += float(row["iterations_or_trials"])
        stats["time_seconds_total"] += float(row["time_seconds"])

    summary = []
    for method, stats in sorted(by_method.items()):
        row_count = int(stats["rows"])
        summary.append(
            {
                "method": method,
                "rows": row_count,
                "converged": int(stats["converged"]),
                "convergence_rate": fmt_float(stats["converged"] / row_count if row_count else None),
                "other_root": int(stats["other_root"]),
                "other_root_rate": fmt_float(stats["other_root"] / row_count if row_count else None),
                "decision_evaluated": int(stats["decision_evaluated"]),
                "decision_mismatch": int(stats["decision_mismatch"]),
                "decision_mismatch_rate": fmt_float(
                    stats["decision_mismatch"] / stats["decision_evaluated"]
                    if stats["decision_evaluated"]
                    else None
                ),
                "avg_root_error_to_relevant_bps": fmt_float(
                    stats["root_error_bps_total"] / stats["root_error_bps_count"]
                    if stats["root_error_bps_count"]
                    else None
                ),
                "avg_iterations_or_trials": fmt_float(stats["iterations_or_trials_total"] / row_count if row_count else None),
                "avg_time_seconds": fmt_float(stats["time_seconds_total"] / row_count if row_count else None),
            }
        )
    return summary


def write_csv(path: Path, rows: Sequence[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "case_type",
        "cashflow_type",
        "period_count",
        "rrr",
        "npv_at_rrr",
        "decision",
        "sign_changes",
        "detected_irr_count",
        "multiple_irr_detected",
        "detected_irrs",
        "decision_relevant_irr",
        "rrr_to_decision_relevant_bps",
        "method",
        "decision_rule",
        "seed",
        "root",
        "npv_at_root",
        "root_error_to_relevant_bps",
        "root_relation",
        "method_decision_from_root",
        "method_decision",
        "decision_matches_npv",
        "converged",
        "status",
        "iterations_or_trials",
        "time_seconds",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_csv(path: Path, rows: Sequence[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "method",
        "rows",
        "converged",
        "convergence_rate",
        "other_root",
        "other_root_rate",
        "decision_evaluated",
        "decision_mismatch",
        "decision_mismatch_rate",
        "avg_root_error_to_relevant_bps",
        "avg_iterations_or_trials",
        "avg_time_seconds",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Evbayiro-IRR paper benchmark CSV data.")
    parser.add_argument("--per-type", type=int, default=20, help="Generated cases per cash-flow type.")
    parser.add_argument("--seed", type=int, default=20260528, help="Random seed for reproducibility.")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "benchmarks" / "results" / "paper_benchmark.csv",
        help="Output CSV path.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    cases = generate_cases(args.per_type, args.seed)
    rows: List[dict] = []
    for case in cases:
        rows.extend(benchmark_case(case))

    write_csv(args.out, rows)
    summary_rows = summarize(rows)
    summary_path = args.out.with_name(f"{args.out.stem}_summary.csv")
    write_summary_csv(summary_path, summary_rows)
    print(f"Wrote {len(rows)} method rows across {len(cases)} cases to {args.out}")
    print(f"Wrote method summary to {summary_path}")
    for stats in summary_rows:
        print(
            f"{stats['method']}: rows={stats['rows']}, converged={stats['converged']}, "
            f"other_root={stats['other_root']}, other_root_rate={stats['other_root_rate']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
