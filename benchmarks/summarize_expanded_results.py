"""Create grouped summaries for the expanded benchmark."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Callable, Optional, Sequence

from paper_benchmark import summarize, write_summary_csv

ROOT = Path(__file__).resolve().parents[1]


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_case_mix(path: Path, rows: list[dict]) -> None:
    case_type_by_id = {row["case_id"]: row["case_type"] for row in rows}
    cashflow_type_by_id = {row["case_id"]: row["cashflow_type"] for row in rows}
    type_counts = Counter(case_type_by_id.values())
    cashflow_counts = Counter(cashflow_type_by_id.values())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["metric", "category", "count"])
        for category, count in sorted(type_counts.items()):
            writer.writerow(["case_type", category, count])
        for category, count in sorted(cashflow_counts.items()):
            writer.writerow(["cashflow_type", category, count])
        writer.writerow(["total_cases", "all", len(case_type_by_id)])
        writer.writerow(["total_method_rows", "all", len(rows)])


def write_grouped_summary(
    out_path: Path,
    rows: list[dict],
    groups: Sequence[tuple[str, Callable[[dict], bool]]],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "group",
        "method",
        "rows",
        "cases",
        "converged",
        "convergence_rate",
        "root_applicable",
        "root_converged_applicable",
        "root_convergence_applicable_rate",
        "other_root",
        "other_root_rate",
        "decision_evaluated",
        "decision_mismatch",
        "decision_mismatch_rate",
        "avg_root_error_to_relevant_bps",
        "avg_iterations_or_trials",
        "avg_time_seconds",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for group_name, predicate in groups:
            subset = [row for row in rows if predicate(row)]
            case_count = len({row["case_id"] for row in subset})
            for summary_row in summarize(subset):
                row = dict(summary_row)
                row["group"] = group_name
                row["cases"] = case_count
                writer.writerow(row)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize expanded Evbayiro benchmark results.")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "benchmarks" / "results" / "expanded_benchmark.csv",
        help="Expanded benchmark CSV.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "benchmarks" / "results" / "expanded_benchmark_group_summary.csv",
        help="Grouped summary CSV.",
    )
    parser.add_argument(
        "--case-mix",
        type=Path,
        default=ROOT / "benchmarks" / "results" / "expanded_benchmark_case_mix.csv",
        help="Case mix summary CSV.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rows = read_rows(args.input)
    groups = [
        ("all", lambda row: True),
        ("sourced_public", lambda row: row["case_type"].startswith("sourced")),
        ("sec_company_proxy", lambda row: row["case_type"] == "sec_company_fcf_proxy"),
        (
            "generated_stress",
            lambda row: row["case_type"].startswith("generated") or row["case_type"].startswith("manuscript"),
        ),
        ("conventional", lambda row: row["cashflow_type"] == "conventional"),
        ("non_conventional", lambda row: row["cashflow_type"] == "non_conventional"),
    ]
    write_grouped_summary(args.out, rows, groups)
    write_case_mix(args.case_mix, rows)
    # Keep a plain all-method summary beside the grouped file.
    write_summary_csv(args.input.with_name(f"{args.input.stem}_summary.csv"), summarize(rows))
    print(f"Wrote grouped summary to {args.out}")
    print(f"Wrote case mix to {args.case_mix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
