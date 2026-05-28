"""Run Evbayiro-IRR benchmarks on sourced public teaching cases."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from paper_benchmark import BenchmarkCase, benchmark_case, summarize, write_csv, write_summary_csv


def parse_cashflows(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(";") if part.strip())


def load_cases(path: Path) -> list[tuple[BenchmarkCase, dict]]:
    cases = []
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            case = BenchmarkCase(
                case_id=row["case_id"],
                case_type=row["case_type"],
                cashflows=parse_cashflows(row["cashflows"]),
                rrr=float(row["rrr"]),
            )
            cases.append((case, row))
    return cases


def add_source_metadata(rows: list[dict], source_row: dict) -> list[dict]:
    enriched = []
    for row in rows:
        merged = dict(row)
        merged["source_name"] = source_row["source_name"]
        merged["source_url"] = source_row["source_url"]
        merged["rrr_note"] = source_row["rrr_note"]
        merged["source_case_note"] = source_row.get("source_case_note", "")
        enriched.append(merged)
    return enriched


def write_sourced_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    base_fields = [
        "case_id",
        "case_type",
        "source_name",
        "source_url",
        "rrr_note",
        "source_case_note",
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
        writer = csv.DictWriter(file, fieldnames=base_fields)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark sourced public Evbayiro-IRR cases.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT / "benchmarks" / "sourced_cases.csv",
        help="CSV file containing sourced cash-flow cases.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "benchmarks" / "results" / "sourced_benchmark.csv",
        help="Output CSV path.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rows = []
    for case, source_row in load_cases(args.cases):
        rows.extend(add_source_metadata(benchmark_case(case), source_row))

    write_sourced_csv(args.out, rows)
    summary_rows = summarize(rows)
    summary_path = args.out.with_name(f"{args.out.stem}_summary.csv")
    write_summary_csv(summary_path, summary_rows)

    print(f"Wrote {len(rows)} method rows from {len(load_cases(args.cases))} sourced cases to {args.out}")
    print(f"Wrote method summary to {summary_path}")
    for stats in summary_rows:
        print(
            f"{stats['method']}: rows={stats['rows']}, converged={stats['converged']}, "
            f"other_root={stats['other_root']}, other_root_rate={stats['other_root_rate']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
