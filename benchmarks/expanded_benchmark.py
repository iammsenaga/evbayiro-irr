"""Run an expanded benchmark across sourced, company-proxy, and stress cases."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from paper_benchmark import BenchmarkCase, benchmark_case, generate_cases, summarize, write_summary_csv
from sourced_benchmark import add_source_metadata, load_cases, write_sourced_csv

ROOT = Path(__file__).resolve().parents[1]


def generated_source_row(case: BenchmarkCase) -> dict:
    return {
        "source_name": "Generated stress case",
        "source_url": "",
        "rrr_note": "Scenario RRR assigned by deterministic benchmark generator.",
        "source_case_note": f"{case.case_type}; generated for robustness testing, not an external published case.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run expanded Evbayiro-IRR comparative benchmark.")
    parser.add_argument(
        "--sourced-cases",
        type=Path,
        default=ROOT / "benchmarks" / "sourced_cases.csv",
        help="Public teaching/project cases CSV.",
    )
    parser.add_argument(
        "--company-cases",
        type=Path,
        default=ROOT / "benchmarks" / "company_proxy_cases.csv",
        help="SEC company proxy cases CSV.",
    )
    parser.add_argument("--target-cases", type=int, default=220, help="Approximate total case count.")
    parser.add_argument("--seed", type=int, default=20260528, help="Generated case seed.")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "benchmarks" / "results" / "expanded_benchmark.csv",
        help="Output benchmark CSV path.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rows = []
    case_count = 0

    for path in (args.sourced_cases, args.company_cases):
        if not path.exists():
            continue
        for case, source_row in load_cases(path):
            rows.extend(add_source_metadata(benchmark_case(case), source_row))
            case_count += 1

    remaining = max(0, args.target_cases - case_count)
    generated_per_type = max(0, (remaining + 1) // 2)
    generated = generate_cases(generated_per_type, args.seed)
    for case in generated[:remaining]:
        rows.extend(add_source_metadata(benchmark_case(case), generated_source_row(case)))
        case_count += 1

    write_sourced_csv(args.out, rows)
    summary_rows = summarize(rows)
    summary_path = args.out.with_name(f"{args.out.stem}_summary.csv")
    write_summary_csv(summary_path, summary_rows)

    print(f"Wrote {len(rows)} method rows across {case_count} cases to {args.out}")
    print(f"Wrote method summary to {summary_path}")
    for stats in summary_rows:
        print(
            f"{stats['method']}: rows={stats['rows']}, converged={stats['converged']}, "
            f"other_root={stats['other_root']}, mismatch={stats['decision_mismatch']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
