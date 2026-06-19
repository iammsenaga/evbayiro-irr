"""Evbayiro RRR-First Method for decision-anchored IRR analysis."""

from .cashflows import cashflow_signs, classify_cashflows, count_sign_changes
from .core import EVBAYIRO_CONSTANT, DEFAULT_STEP, linear_interpolate_root, npv
from .e3c import E3CResult, e3c_close_once, iterated_e3c, scaled_zero_npv_residual
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
from .solvers import bisection_irr, brent_irr, newton_irr, secant_irr

__all__ = [
    "EVBAYIRO_CONSTANT",
    "DEFAULT_STEP",
    "CashflowType",
    "Decision",
    "E3CResult",
    "EvbayiroResult",
    "IRRBracket",
    "SearchDirection",
    "SolverResult",
    "TrialPoint",
    "bisection_irr",
    "brent_irr",
    "cashflow_signs",
    "classify_cashflows",
    "count_sign_changes",
    "e3c_close_once",
    "evbayiro_analysis",
    "iterated_e3c",
    "linear_interpolate_root",
    "newton_irr",
    "npv",
    "scaled_zero_npv_residual",
    "secant_irr",
]

__version__ = "0.2.0"
