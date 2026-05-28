# Evbayiro-IRR Benchmark Dataset

This dataset supports reproducible evaluation of Evbayiro-IRR against standard
IRR root-finding methods.

Dataset concept DOI: https://doi.org/10.5281/zenodo.20429257

Current dataset package version: 1.1.1

The dataset has three parts:

- `sourced_cases.csv` and `results/sourced_benchmark*.csv`: public online
  teaching and reference cases used as the primary external evidence set.
- `results/paper_benchmark*.csv`: generated and manuscript-derived stress cases
  used as supplementary robustness evidence.
- `company_proxy_cases.csv` and `results/expanded_benchmark*.csv`: expanded
  robustness evidence combining sourced cases, generated stress cases, and
  SEC Companyfacts firm-level free-cash-flow proxy sequences.

The current result files are:

- `results/sourced_benchmark_expanded_methods.csv`
- `results/sourced_benchmark_expanded_methods_summary.csv`
- `results/expanded_benchmark.csv`
- `results/expanded_benchmark_summary.csv`
- `results/expanded_benchmark_group_summary.csv`
- `results/expanded_benchmark_case_mix.csv`

Earlier result files from the first benchmark release are intentionally omitted
from the current package to avoid mixing superseded and current evidence.

Some non-conventional cash-flow sequences do not have an economically valid
real IRR boundary even though their signs change more than once. These rows are
kept in the dataset and marked with `root_applicable = False` so that decision
completion and IRR-boundary convergence are not confused.

The sourced benchmark is the primary dataset for external validation because it
records the source name, source URL, required rate of return notes, cash-flow
pattern, method output, convergence status, root relation, decision match, and
timing fields.

The generated benchmark is included for transparency and repeatability. It
should be labelled as simulated stress evidence in manuscripts rather than as
external published-case evidence.

The SEC company proxy cases should be labelled carefully. They are public,
company-level accounting sequences built from SEC Companyfacts data; they are
not disclosed project appraisal cash flows and should not be described as real
corporate capital-budgeting project cases.

## Software

The benchmark was generated with Evbayiro-IRR 0.1.1.

- GitHub: https://github.com/iammsenaga/evbayiro-irr
- PyPI: https://pypi.org/project/evbayiro-irr/
- Software DOI: https://doi.org/10.5281/zenodo.20428636

## Regeneration

From the repository root:

```powershell
python -m pip install -r benchmarks\requirements.txt --target .benchmark_deps
python benchmarks\sourced_benchmark.py
python benchmarks\paper_benchmark.py --per-type 10
python benchmarks\company_proxy_cases.py --limit 50
python benchmarks\expanded_benchmark.py --target-cases 220
python benchmarks\summarize_expanded_results.py
```

## Interpretation

`evbayiro_rrr_first` reports the RRR-anchored decision and the
decision-relevant IRR boundary. Newton-Raphson and Secant rows are repeated with
different initial guesses to expose seed sensitivity. `excel_default_guess_proxy`
uses the package Newton implementation with a 10% default starting value and a
20-iteration limit as a transparent proxy for Excel-style default-guess behavior;
it is not an exact reimplementation of Microsoft Excel. `numpy_financial_irr`
and `pyxirr_irr` evaluate common Python finance-library interfaces.
`bisection_known_bracket` is a control method that receives the known
decision-relevant bracket and is not used as a normal unanchored competitor.
