# Evbayiro-IRR

[![PyPI version](https://img.shields.io/pypi/v/evbayiro-irr.svg)](https://pypi.org/project/evbayiro-irr/)
[![CI](https://github.com/iammsenaga/evbayiro-irr/actions/workflows/ci.yml/badge.svg)](https://github.com/iammsenaga/evbayiro-irr/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20428635.svg)](https://doi.org/10.5281/zenodo.20428635)
[![Benchmark DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20514086.svg)](https://doi.org/10.5281/zenodo.20514086)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Evbayiro-IRR is an open-source Python library for decision-first capital
budgeting analysis. It implements the Evbayiro RRR-First Method, an anchored IRR
workflow that begins with the Required Rate of Return (RRR), evaluates NPV at
that decision point, and then interprets IRR boundaries in context.

Unlike a bare `irr()` function, Evbayiro-IRR returns a structured analysis:
the NPV decision at the RRR, the cash-flow pattern, the anchored trial path,
any detected IRR boundaries, and warnings for non-conventional cash flows.

Version 0.2.0 closes each Evbayiro 1% sign-changing bracket with the Evbayiro
Three-Point Curvature Closure (E3C). The main analysis workflow does not use
linear interpolation, bisection, Brent's method, Newton-Raphson, or the secant
method to produce its IRR estimate. Those standard solvers remain available
only as explicit comparison utilities.

## Quick Start

```python
from evbayiro_irr import evbayiro_analysis

result = evbayiro_analysis(
    cashflows=[-350000, 125000, 150000, 170000],
    rrr=0.11,
)

print(result.decision)       # accept
print(result.anchor_npv)     # NPV at 11%
print(result.estimated_irr)  # Evbayiro E3C IRR
print(result.trial_path)     # transparent 1% search path
```

The main result fields include:

- `decision`: accept, reject, breakeven, or not evaluated.
- `anchor_npv`: NPV at the supplied RRR or provisional anchor.
- `cashflow_type`: conventional, non-conventional, or no-IRR pattern.
- `trial_path`: the 1% anchored search path.
- `estimated_irr`: Iterated E3C estimate from the anchored bracket.
- `detected_irrs`: detected anchor-contiguous IRR boundaries for
  non-conventional cash flows.
- `decision_relevant_irr`: the IRR boundary relevant to the RRR region.
- `closure_scaled_residual`: scaled zero-NPV residual after E3C closure.

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
print(result.detected_irrs)              # detected anchor-contiguous boundaries
print(result.decision_relevant_irr)      # boundary around the RRR region
print(result.decision)                   # accept, based on NPV at RRR
print(result.warnings)
```

For non-conventional patterns, Evbayiro-IRR does not treat a single IRR as the
final decision rule. It keeps NPV at the RRR as the controlling accept/reject
test, searches upward and downward from the anchor for adjacent 1% sign-change
boundaries, closes each detected boundary with E3C, and identifies the boundary
relevant to the RRR region.

## Algorithm

For conventional cash flows, the library:

1. evaluates NPV at the supplied RRR;
2. moves in adjacent 1% steps in the direction implied by the anchor NPV;
3. stops at the first adjacent sign-changing bracket; and
4. applies Iterated E3C until the scaled zero-NPV residual meets the requested
   tolerance or the iteration cap is reached.

For non-conventional cash flows, the library scans both upward and downward
from the RRR, closes each detected anchor-contiguous bracket with Iterated E3C,
and reports the boundary relevant to the RRR decision region. NPV at the RRR,
not an isolated IRR value, remains the controlling accept/reject rule.

The default residual is:

```text
R(r) = |NPV(r)| / sum(|CF_t|)
```

## Design Goals

- Anchor the first calculation at the RRR.
- Use the Evbayiro Constant of 10% only when no RRR is supplied.
- Preserve the NPV decision rule.
- Use a deterministic 1% step protocol by default.
- Close Evbayiro brackets with the Evbayiro Three-Point Curvature Closure
  (E3C).
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

- Software concept DOI: https://doi.org/10.5281/zenodo.20428635
- Version 0.2.0 software DOI: https://doi.org/10.5281/zenodo.20767632
- Dataset concept DOI: https://doi.org/10.5281/zenodo.20429257
- Latest dataset version DOI: https://doi.org/10.5281/zenodo.20514086
- Current benchmark package: 88,556 SEC/Damodaran public-company cash-flow
  proxy cases.
- Comparative interfaces include Evbayiro RRR-First, Newton-Raphson, Secant,
  an Excel-style default-guess proxy, `numpy_financial.irr`, `pyxirr.irr`, and
  known-bracket bisection as a control.
