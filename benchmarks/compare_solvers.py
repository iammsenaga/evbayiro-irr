"""Small benchmark/demo for Evbayiro against numerical solvers."""

from __future__ import annotations

from time import perf_counter

from evbayiro_irr import evbayiro_analysis, newton_irr, secant_irr
from evbayiro_irr.examples import (
    manuscript_example_2,
    manuscript_non_conventional_example,
)


def timed(label, callback):
    start = perf_counter()
    result = callback()
    elapsed = perf_counter() - start
    return label, result, elapsed


def show_solver(label, result, elapsed):
    root = "None" if result.root is None else f"{result.root:.6%}"
    print(f"{label:34} root={root:>12} iterations={result.iterations:>3} time={elapsed:.8f}s")


def main():
    cases = [
        ("Conventional example 2", manuscript_example_2(), 0.11),
        ("Non-conventional stress test", manuscript_non_conventional_example(), 0.15),
    ]

    for name, cashflows, rrr in cases:
        print(f"\n{name}")
        label, result, elapsed = timed(
            "Evbayiro RRR-first",
            lambda: evbayiro_analysis(cashflows, rrr=rrr),
        )
        irr = "None" if result.decision_relevant_irr is None else f"{result.decision_relevant_irr:.6%}"
        print(
            f"{label:34} irr={irr:>13} decision={result.decision.value:<10} "
            f"trials={len(result.trial_path):>3} time={elapsed:.8f}s"
        )

        for seed in (0.05, rrr, 0.30):
            label, solver_result, elapsed = timed(
                f"Newton seed {seed:.0%}",
                lambda seed=seed: newton_irr(cashflows, initial_guess=seed),
            )
            show_solver(label, solver_result, elapsed)

        for first, second in ((0.0, 0.10), (rrr, rrr + 0.01), (0.20, 0.30)):
            label, solver_result, elapsed = timed(
                f"Secant seeds {first:.0%},{second:.0%}",
                lambda first=first, second=second: secant_irr(
                    cashflows,
                    first_guess=first,
                    second_guess=second,
                ),
            )
            show_solver(label, solver_result, elapsed)


if __name__ == "__main__":
    main()

