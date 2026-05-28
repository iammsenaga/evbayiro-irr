"""Build public-company cash-flow proxy cases from SEC Companyfacts data.

These are not disclosed project appraisal cases. They are firm-level proxy
sequences that use one fiscal year's capital expenditure as the initial outflow
and subsequent annual free cash flow as inflows/outflows.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path
from typing import Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "benchmarks" / "company_proxy_cases.csv"
USER_AGENT = "Evbayiro-IRR research benchmark contact: senaga.tech.hub@gmail.com"

COMPANIES = [
    ("AAPL", 320193),
    ("MSFT", 789019),
    ("AMZN", 1018724),
    ("GOOGL", 1652044),
    ("META", 1326801),
    ("NVDA", 1045810),
    ("TSLA", 1318605),
    ("JPM", 19617),
    ("BAC", 70858),
    ("WMT", 104169),
    ("XOM", 34088),
    ("CVX", 93410),
    ("PFE", 78003),
    ("KO", 21344),
    ("PEP", 77476),
    ("DIS", 1744489),
    ("NFLX", 1065280),
    ("ADBE", 796343),
    ("CSCO", 858877),
    ("INTC", 50863),
    ("ORCL", 1341439),
    ("CRM", 1108524),
    ("IBM", 51143),
    ("GE", 40545),
    ("F", 37996),
    ("GM", 1467858),
    ("BA", 12927),
    ("CAT", 18230),
    ("MCD", 63908),
    ("NKE", 320187),
    ("SBUX", 829224),
    ("HD", 354950),
    ("LOW", 60667),
    ("COST", 909832),
    ("TGT", 27419),
    ("T", 732717),
    ("VZ", 732712),
    ("CMCSA", 1166691),
    ("UPS", 1090727),
    ("FDX", 1048911),
    ("DAL", 27904),
    ("AAL", 6201),
    ("UAL", 100517),
    ("LUV", 92380),
    ("C", 831001),
    ("WFC", 72971),
    ("GS", 886982),
    ("MS", 895421),
    ("BRK", 1067983),
    ("UNH", 731766),
    ("JNJ", 200406),
    ("MRK", 310158),
    ("ABBV", 1551152),
    ("TMO", 97745),
    ("ABT", 1800),
    ("AMD", 2488),
    ("QCOM", 804328),
    ("TXN", 97476),
    ("AMAT", 6951),
    ("LRCX", 707549),
]

OPERATING_CASH_FLOW_TAGS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
]
CAPEX_TAGS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
]


def fetch_companyfacts(cik: int) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def annual_usd_values(facts: dict, tag_names: Sequence[str]) -> dict[int, float]:
    for tag in tag_names:
        if tag not in facts:
            continue
        units = facts[tag].get("units", {})
        if "USD" not in units:
            continue
        by_year: dict[int, tuple[str, float]] = {}
        for item in units["USD"]:
            if item.get("form") != "10-K" or item.get("fp") != "FY":
                continue
            fy = item.get("fy")
            filed = item.get("filed") or ""
            value = item.get("val")
            if fy is None or value is None:
                continue
            year = int(fy)
            if year not in by_year or filed > by_year[year][0]:
                by_year[year] = (filed, float(value))
        if by_year:
            return {year: value for year, (_, value) in by_year.items()}
    return {}


def build_case(ticker: str, cik: int, *, rrr: float) -> Optional[dict]:
    data = fetch_companyfacts(cik)
    facts = data.get("facts", {}).get("us-gaap", {})
    cfo = annual_usd_values(facts, OPERATING_CASH_FLOW_TAGS)
    capex = annual_usd_values(facts, CAPEX_TAGS)
    years = sorted(set(cfo) & set(capex))
    if len(years) < 6:
        return None

    # Use the latest six-year window with complete CFO and capex data.
    window = years[-6:]
    base_year = window[0]
    future_years = window[1:]
    initial_outflow = -abs(capex[base_year])
    future_fcf = [cfo[year] - abs(capex[year]) for year in future_years]
    cashflows = [initial_outflow, *future_fcf]
    if initial_outflow == 0 or all(value == 0 for value in future_fcf):
        return None

    name = data.get("entityName", ticker)
    case_id = f"sec_{ticker.lower()}_{base_year}_{window[-1]}_fcf_proxy"
    source_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    note = (
        f"Firm-level proxy, not a disclosed project case: CF0 is FY{base_year} capex; "
        f"CF1-CF5 are annual free cash flow estimates (operating cash flow minus capex) "
        f"for FY{future_years[0]}-FY{future_years[-1]}."
    )
    return {
        "case_id": case_id,
        "case_type": "sec_company_fcf_proxy",
        "source_name": f"SEC Companyfacts - {name} ({ticker})",
        "source_url": source_url,
        "rrr": f"{rrr:.12g}",
        "rrr_note": f"Scenario hurdle rate set to {rrr:.0%}; company WACC is not asserted.",
        "cashflows": ";".join(f"{value:.12g}" for value in cashflows),
        "source_case_note": note,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate SEC public-company proxy cash-flow cases.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output CSV path.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum company proxy cases to write.")
    parser.add_argument("--rrr", type=float, default=0.10, help="Scenario hurdle rate.")
    parser.add_argument("--sleep", type=float, default=0.12, help="Delay between SEC requests.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    rows = []
    for ticker, cik in COMPANIES:
        try:
            row = build_case(ticker, cik, rrr=args.rrr)
        except Exception as error:
            print(f"Skipping {ticker}: {type(error).__name__}: {error}")
            row = None
        if row is not None:
            rows.append(row)
            print(f"Added {ticker}: {row['case_id']}")
        if len(rows) >= args.limit:
            break
        time.sleep(args.sleep)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "case_type",
        "source_name",
        "source_url",
        "rrr",
        "rrr_note",
        "cashflows",
        "source_case_note",
    ]
    with args.out.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} company proxy cases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
