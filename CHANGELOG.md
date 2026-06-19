# Changelog

## 0.2.0 - 2026-06-19

- Replaced the Evbayiro workflow's two-point interpolation closure with the
  Evbayiro Three-Point Curvature Closure (E3C).
- Added Iterated E3C with the scaled zero-NPV residual
  `R(r) = |NPV(r)| / sum(|CF_t|)` and a configurable iteration cap.
- Corrected non-conventional analysis to scan both upward and downward from
  the RRR and report anchor-contiguous IRR boundaries.
- Added closure method, status, iteration count, and residual fields to the
  structured result and command-line output.
- Exposed one-step E3C, Iterated E3C, and residual helpers through the public
  Python API.
- Added Brent's method as a known-bracket comparison solver; it is not used by
  the Evbayiro analysis workflow.
- Expanded tests for E3C closure, bidirectional non-conventional analysis,
  result reporting, and comparison solvers.

## 0.1.1 - 2026-05-28

- Added public repository badges to the README.
- Prepared the release stream for software DOI archiving.

## 0.1.0 - 2026-05-28

- Initial public release of Evbayiro-IRR.
- Added RRR-first NPV decision analysis.
- Added conventional, non-conventional, and no-IRR cash-flow classification.
- Added deterministic 1% anchored search path.
- Added non-conventional cash-flow diagnostics and decision-relevant IRR labeling.
- Added Newton-Raphson, Secant, and known-bracket bisection comparison solvers.
- Added command-line interface and JSON output.
- Added unit tests and benchmark scripts.
