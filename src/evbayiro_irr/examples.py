"""Cash-flow examples used by the manuscript and tests."""

from __future__ import annotations

from typing import Tuple


def manuscript_example_1() -> Tuple[float, ...]:
    """Return the first manuscript example as period cash flows."""

    return (0.0, *([-5000.0] * 5), *([5000.0] * 15))


def manuscript_example_2() -> Tuple[float, ...]:
    """Return the Mr. Amila teaching example."""

    return (-350000.0, 125000.0, 150000.0, 170000.0)


def manuscript_non_conventional_example() -> Tuple[float, ...]:
    """Return the non-conventional mining-project stress test."""

    return (-1000000.0, 800000.0, 1000000.0, 1350000.0, -2250000.0)

