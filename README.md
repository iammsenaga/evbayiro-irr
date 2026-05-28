# Evbayiro-IRR

[![PyPI version](https://img.shields.io/pypi/v/evbayiro-irr.svg)](https://pypi.org/project/evbayiro-irr/)
[![CI](https://github.com/iammsenaga/evbayiro-irr/actions/workflows/ci.yml/badge.svg)](https://github.com/iammsenaga/evbayiro-irr/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20428636.svg)](https://doi.org/10.5281/zenodo.20428636)
[![Benchmark DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20429258.svg)](https://doi.org/10.5281/zenodo.20429258)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Evbayiro-IRR is an open-source Python library for decision-first capital
budgeting analysis. It implements the Evbayiro RRR-First Method, an anchored IRR
workflow that begins with the Required Rate of Return (RRR), evaluates NPV at
that decision point, and then interprets IRR boundaries in context.

Unlike a bare `irr()` function, Evbayiro-IRR returns a structured analysis:
the NPV decision at the RRR, the cash-flow pattern, the anchored trial path,
any detected IRR boundaries, and warnings for non-conventional cash flows.

## Quick Start

```python
from evbayiro_irr import evbayiro_analysis

result = evbayiro_analysis(
    cashflows=[-350000, 125000, 150000, 170000],
    rrr=0.11,
)

print(result.decision)       # accept
print(result.anchor_npv)     # NPV at 11%
print(result.estimated_irr)  # Evbayiro interpolated IRR
print(result.trial_path)     # transparent 1% search path
```

The main result fields include:

- `decision`: accept, reject, breakeven, or not evaluated.
- `anchor_npv`: NPV at the supplied RRR or provisional anchor.
- `cashflow_type`: conventional, non-conventional, or no-IRR pattern.
- `trial_path`: the 1% anchored search path.
- `estimated_irr`: interpolated Evbayiro estimate from the anchored bracket.
- `detected_irrs`: detected IRR boundaries for non-conventional cash flows.
- `decision_relevant_irr`: the IRR boundary relevant to the RRR region.

## Command Line

After installation, run a conventional example:

```powershell
evbayiro-irr --cashflows -350000 125000 150000 170000 --rrr 11%
```

Run a non-conventional cash-flow example:

```powershell
evbayiro-irr --cashflows -1000000 800000 1000000 1350000 -2250000 --rrr 15%
```

Rates may be supplied as `0.15`, `15%`, or `15`. Use `--json` for
machine-readable output, `--show-path` to print every trial rate, and
`--version` to print the installed package version.

## Non-Conventional Cash Flows

The library detects non-conventional cash flows automatically by counting sign
changes in the cash-flow sequence.

```python
from evbayiro_irr import evbayiro_analysis

result = evbayiro_analysis(
    cashflows=[-1000000, 800000, 1000000, 1350000, -2250000],
    rrr=0.15,
)

print(result.cashflow_type)              # non_conventional
print(result.detected_irrs)              # all detected IRR boundaries
print(result.decision_relevant_irr)      # boundary around the RRR region
print(result.decision)                   # accept, based on NPV at RRR
print(result.warnings)
```

For non-conventional patterns, Evbayiro-IRR does not treat a single IRR as the
final decision rule. It keeps NPV at the RRR as the controlling accept/reject
test, reports detected IRR boundaries, and identifies the boundary relevant to
the RRR region.

## Design Goals

- Anchor the first calculation at the RRR.
- Use the Evbayiro Constant of 10% only when no RRR is supplied.
- Preserve the NPV decision rule.
- Use a deterministic 1% step protocol by default.
- Detect conventional and non-conventional cash-flow patterns automatically.
- Produce transparent trial paths for teaching, review, and professional
  interpretation.

## Development

Run the tests with:

```powershell
python -m unittest discover -s tests
```

## Research Data

The benchmark dataset used for comparative analysis is archived separately:

- Dataset concept DOI: https://doi.org/10.5281/zenodo.20429257
- Latest dataset version DOI: https://doi.org/10.5281/zenodo.20435350
- Current benchmark package: 49 sourced public cases, 50 SEC public-company
  proxy sequences, and generated/manuscript stress cases.
- Comparative interfaces include Evbayiro RRR-First, Newton-Raphson, Secant,
  an Excel-style default-guess proxy, `numpy_financial.irr`, `pyxirr.irr`, and
  known-bracket bisection as a control.
