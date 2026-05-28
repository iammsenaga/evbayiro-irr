# Evbayiro-IRR Benchmark Dataset

This dataset supports reproducible evaluation of Evbayiro-IRR against standard
IRR root-finding methods.

Dataset DOI: https://doi.org/10.5281/zenodo.20429258

The dataset has two parts:

- `sourced_cases.csv` and `results/sourced_benchmark*.csv`: public online
  teaching and reference cases used as the primary external evidence set.
- `results/paper_benchmark*.csv`: generated and manuscript-derived stress cases
  used as supplementary robustness evidence.

The sourced benchmark is the primary dataset for external validation because it
records the source name, source URL, required rate of return notes, cash-flow
pattern, method output, convergence status, root relation, decision match, and
timing fields.

The generated benchmark is included for transparency and repeatability. It
should be labelled as simulated stress evidence in manuscripts rather than as
external published-case evidence.

## Software

The benchmark was generated with Evbayiro-IRR 0.1.1.

- GitHub: https://github.com/iammsenaga/evbayiro-irr
- PyPI: https://pypi.org/project/evbayiro-irr/
- Software DOI: https://doi.org/10.5281/zenodo.20428636

## Regeneration

From the repository root:

```powershell
python benchmarks\sourced_benchmark.py
python benchmarks\paper_benchmark.py --per-type 10
```

## Interpretation

`evbayiro_rrr_first` reports the RRR-anchored decision and the
decision-relevant IRR boundary. Newton-Raphson and Secant rows are repeated with
different initial guesses to expose seed sensitivity. `bisection_known_bracket`
is a control method that receives the known decision-relevant bracket and is not
used as a normal unanchored competitor.
