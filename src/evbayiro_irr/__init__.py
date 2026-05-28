"""Evbayiro RRR-First Method for decision-anchored IRR analysis."""

from .cashflows import cashflow_signs, classify_cashflows, count_sign_changes
from .core import EVBAYIRO_CONSTANT, DEFAULT_STEP, linear_interpolate_root, npv
from .method import evbayiro_analysis
from .results import (
    CashflowType,
    Decision,
    EvbayiroResult,
    IRRBracket,
    SearchDirection,
    SolverResult,
    TrialPoint,
)
from .solvers import bisection_irr, newton_irr, secant_irr

__all__ = [
    "EVBAYIRO_CONSTANT",
    "DEFAULT_STEP",
    "CashflowType",
    "Decision",
    "EvbayiroResult",
    "IRRBracket",
    "SearchDirection",
    "SolverResult",
    "TrialPoint",
    "bisection_irr",
    "cashflow_signs",
    "classify_cashflows",
    "count_sign_changes",
    "evbayiro_analysis",
    "linear_interpolate_root",
    "newton_irr",
    "npv",
    "secant_irr",
]

__version__ = "0.1.1"
