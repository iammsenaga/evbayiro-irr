---
title: 'Evbayiro-IRR: RRR-First Internal Rate of Return Analysis for Capital Budgeting'
authors:
  - name: Osasenaga David Evbayiro
    affiliation: '1'
affiliations:
  - name: Faculty of Veterinary Medicine, University of Benin, Benin City, Nigeria
    index: 1
date: 10 November 2026
tags:
  - Python
  - capital budgeting
  - internal rate of return
  - net present value
  - financial analysis
bibliography: paper.bib
---

# Summary

Evbayiro-IRR is an open-source Python library for analyzing project cash flows when an analyst needs both an internal rate of return (IRR) and an investment decision tied to a required rate of return (RRR). It evaluates net present value (NPV) at the supplied RRR, classifies the cash-flow sign pattern, searches outward from the RRR for adjacent rate intervals that bracket zero NPV, and reports the resulting analysis as structured data. The library also provides a command-line interface and records the rates and NPV values evaluated during the search. It is intended for researchers, instructors, students, and practitioners who need to inspect how a reported IRR relates to a stated hurdle rate rather than receive only a scalar rate.

The package implements the Evbayiro RRR-First Method, whose manual procedure and financial rationale were presented in a foundational capital-budgeting article [@evbayiro_method_2026]. In version 0.2.0, the library closes an adjacent one-percentage-point bracket using the Evbayiro Three-Point Curvature Closure (E3C), with repeated closure governed by a scaled zero-NPV residual and an iteration limit [@evbayiro_software_2026]. The method's anchor is the supplied RRR; when an RRR is omitted, the software can use a provisional 10% search anchor but marks the investment decision as not evaluated.

# Statement of need

An IRR is a rate at which a cash-flow series has zero NPV. That numerical definition does not, by itself, specify the hurdle rate against which a project should be assessed. This distinction matters especially when cash flows change sign more than once: a profile can have multiple zero-NPV rates, so a single returned rate may not communicate which boundary is relevant to the decision region around the organization's RRR. The NPV at the RRR remains the package's controlling accept/reject signal; an IRR estimate is reported as supporting interpretation, not as a replacement for that rule.

General-purpose finance functions and numerical solvers are valuable building blocks, but users often need to compose them with cash-flow diagnostics and decision logic themselves. Evbayiro-IRR packages these tasks in one reproducible workflow. It is designed for capital-budgeting teaching and research that use periodic cash-flow vectors, including analyses where non-conventional patterns require explicit interpretation. It does not infer a firm's RRR, determine whether its assumptions are economically appropriate, or claim to identify every mathematical root over an unrestricted rate domain.

# State of the field

Python users can calculate periodic IRR with `numpy_financial.irr`, which returns a rate solving the zero-NPV equation and supports a selection function when multiple real solutions are found [@numpy_financial]. PyXIRR supplies financial rate-of-return functions, including IRR and date-aware XIRR calculations [@pyxirr]. SciPy provides general scalar root-finding methods, including bracketed methods such as Brent's method and bisection as well as Newton and secant methods [@virtanen2020]. These packages address numerical calculation and financial functions; they are not interchangeable, and each remains useful for its intended workflow.

Evbayiro-IRR occupies a narrower, complementary role. Its design binds the root search to an explicit RRR evaluation, retains an accept/reject signal based on NPV at that anchor, classifies sign changes, and returns the search path and detected anchor-contiguous boundaries alongside the estimate. This distinction is not a claim that existing libraries cannot calculate NPV or handle multiple roots. Rather, Evbayiro-IRR makes the relationship between the hurdle-rate decision and IRR-boundary search an explicit part of the returned analysis. Researchers who need independent control over a root-finding algorithm can use SciPy; those who need a compact IRR function can use NumPy Financial or PyXIRR. The package is useful when the decision context and traceability are part of the analysis output.

# Software design

The implementation separates cash-flow validation and sign-pattern diagnostics from NPV evaluation, rate search, E3C closure, and result reporting. This structure allows the analysis to expose the stages of the calculation without making the user reconstruct them from a solver's internal state. The public result records the decision at the RRR, anchor NPV, cash-flow classification, trial path, detected boundaries, closure status, iteration count, and scaled residual.

For a supplied RRR, the search evaluates NPV at that anchor and steps in adjacent one-percentage-point increments. Conventional cash flows are searched in the direction indicated by the anchor NPV. Non-conventional patterns are scanned both upward and downward, and the software reports detected boundaries contiguous with the anchor region rather than implying that a finite scan is a proof that all possible roots have been found. After a sign-changing interval is identified, E3C uses NPV values at the lower endpoint, midpoint, and upper endpoint to fit a local quadratic closure. Iteration continues until the scaled residual meets the requested tolerance or the configured iteration cap is reached. These limits make non-convergence or a missing boundary reportable states rather than silently treating every input as a successful single-root calculation.

The library has no third-party runtime dependencies, supports Python 3.9 and later, and includes both a Python interface and a command-line entry point. The package is distributed through PyPI and its versioned software archive is preserved on Zenodo [@evbayiro_software_2026]. Automated tests cover conventional and non-conventional patterns, input validation, result fields, E3C behavior, and command-line output. The repository includes continuous integration and release workflows.

# Research impact statement

The software has a published methodological foundation in the RRR-First capital-budgeting procedure [@evbayiro_method_2026] and a public, versioned software archive [@evbayiro_software_2026]. The author used Evbayiro-IRR to carry out the computational validation reported in the published method study, which analyzes 88,556 public-company cash-flow proxy cases [@evbayiro_method_2026]. The associated benchmark materials are archived separately for reuse [@evbayiro_dataset_2026]. Together, the article, software release, and data archive provide a traceable research use case and reusable materials; they do not establish external adoption or comparative superiority, which are not claimed here.

# AI usage disclosure

OpenAI Codex (GPT-5; accessed 10 November 2026) was used to assist with software development and review, testing and documentation, and preparation and editing of this paper. The author reviewed and edited AI-assisted material, checked the software description against the public source repository and release, and is responsible for the accuracy and integrity of the final submission. The core problem framing and algorithmic design decisions remain the author's.

# Acknowledgements

No external financial support was received for this work.

# References
