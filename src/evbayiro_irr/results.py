"""Result objects returned by Evbayiro-IRR."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class CashflowType(str, Enum):
    """Cash-flow pattern classes used by the analysis workflow."""

    CONVENTIONAL = "conventional"
    NON_CONVENTIONAL = "non_conventional"
    NO_IRR_PATTERN = "no_irr_pattern"


class Decision(str, Enum):
    """Decision labels based on the NPV at the supplied RRR."""

    ACCEPT = "accept"
    REJECT = "reject"
    BREAKEVEN = "breakeven"
    NOT_EVALUATED = "not_evaluated"


class SearchDirection(str, Enum):
    """Directional search labels."""

    UPWARD = "upward"
    DOWNWARD = "downward"
    NONE = "none"


@dataclass(frozen=True)
class TrialPoint:
    """A tested discount rate and its NPV."""

    rate: float
    npv: float


@dataclass(frozen=True)
class IRRBracket:
    """A sign-changing interval that contains an IRR boundary."""

    lower_rate: float
    upper_rate: float
    lower_npv: float
    upper_npv: float

    @property
    def width(self) -> float:
        """Return the rate width of the bracket."""

        return self.upper_rate - self.lower_rate

    @property
    def interpolated_rate(self) -> float:
        """Return the linear interpolation estimate for the zero crossing."""

        from .core import linear_interpolate_root

        return linear_interpolate_root(
            self.lower_rate,
            self.lower_npv,
            self.upper_rate,
            self.upper_npv,
        )

    def contains_rate(self, rate: float) -> bool:
        """Return True when `rate` lies inside the bracket."""

        return self.lower_rate <= rate <= self.upper_rate


@dataclass(frozen=True)
class EvbayiroResult:
    """Full audit result for the Evbayiro RRR-First Method."""

    cashflows: Tuple[float, ...]
    rrr: Optional[float]
    anchor_rate: float
    anchor_npv: float
    decision: Decision
    decision_basis: str
    cashflow_type: CashflowType
    sign_changes: int
    search_direction: SearchDirection
    trial_path: Tuple[TrialPoint, ...]
    bracket: Optional[IRRBracket]
    estimated_irr: Optional[float]
    detected_brackets: Tuple[IRRBracket, ...]
    detected_irrs: Tuple[float, ...]
    decision_relevant_bracket: Optional[IRRBracket]
    decision_relevant_irr: Optional[float]
    warnings: Tuple[str, ...]

    @property
    def is_viable(self) -> Optional[bool]:
        """Return the RRR viability decision when an actual RRR was supplied."""

        if self.decision in {Decision.ACCEPT, Decision.BREAKEVEN}:
            return True
        if self.decision is Decision.REJECT:
            return False
        return None


@dataclass(frozen=True)
class SolverResult:
    """Result object for comparison root-finding methods."""

    method: str
    root: Optional[float]
    npv_at_root: Optional[float]
    iterations: int
    converged: bool
    status: str
    path: Tuple[TrialPoint, ...]

