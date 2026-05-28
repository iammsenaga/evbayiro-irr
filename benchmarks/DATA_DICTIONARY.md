# Data Dictionary

## Case Fields

- `case_id`: unique case identifier.
- `case_type`: source or scenario category.
- `source_name`: source title for sourced cases.
- `source_url`: URL for sourced cases.
- `rrr_note`: note explaining how the required rate of return was chosen.
- `source_case_note`: short description of the sourced case.
- `cashflow_type`: conventional, non_conventional, or no_irr_pattern.
- `period_count`: number of post-initial periods.
- `rrr`: required rate of return as a decimal.
- `npv_at_rrr`: NPV evaluated at the RRR.
- `decision`: NPV-at-RRR decision.
- `sign_changes`: number of sign changes after ignoring zero cash flows.
- `detected_irr_count`: count of detected IRR boundaries.
- `multiple_irr_detected`: true when more than one IRR boundary is detected.
- `detected_irrs`: detected roots separated by `|`.
- `decision_relevant_irr`: IRR boundary relevant to the RRR region.
- `rrr_to_decision_relevant_bps`: basis-point distance between RRR and the
  decision-relevant IRR.

## Method Fields

- `method`: evaluated method.
- `decision_rule`: decision rule applied by the method row.
- `seed`: Newton/Secant seed, Excel-proxy default guess, or known bisection
  bracket.
- `root`: returned IRR root.
- `npv_at_root`: NPV at the returned root.
- `root_error_to_relevant_bps`: basis-point distance from the
  decision-relevant IRR.
- `root_relation`: decision_relevant, other_root, none, or not_applicable.
- `method_decision_from_root`: accept/reject result implied by comparing root
  to RRR.
- `method_decision`: decision attributed to the method row.
- `decision_matches_npv`: whether method decision agrees with NPV-at-RRR law.
- `converged`: whether the method returned a root successfully.
- `status`: solver status.
- `iterations_or_trials`: iteration or trial count.
- `time_seconds`: elapsed runtime for the method row.

## Method Labels

- `evbayiro_rrr_first`: Evbayiro-IRR result using the RRR as the anchor.
- `newton`: Newton-Raphson solver rows under three starting seeds.
- `secant`: Secant solver rows under three seed pairs.
- `excel_default_guess_proxy`: Newton-based transparent proxy using a 10%
  default starting guess and 20-iteration limit; not an exact Microsoft Excel
  reimplementation.
- `numpy_financial_irr`: `numpy_financial.irr` scalar finance-function output.
- `pyxirr_irr`: `pyxirr.irr` finance-library output.
- `bisection_known_bracket`: control row using the known decision-relevant
  bracket in advance.
