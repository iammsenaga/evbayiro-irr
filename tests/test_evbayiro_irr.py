import io
import unittest
from contextlib import redirect_stdout

from evbayiro_irr import (
    CashflowType,
    Decision,
    SearchDirection,
    bisection_irr,
    classify_cashflows,
    count_sign_changes,
    evbayiro_analysis,
    newton_irr,
    npv,
    secant_irr,
)
from evbayiro_irr.examples import (
    manuscript_example_1,
    manuscript_example_2,
    manuscript_non_conventional_example,
)
from evbayiro_irr.cli import format_result, main, parse_number, parse_rate


class EvbayiroIRRTests(unittest.TestCase):
    def test_conventional_cashflow_classification(self):
        cashflows = manuscript_example_2()
        self.assertEqual(count_sign_changes(cashflows), 1)
        self.assertEqual(classify_cashflows(cashflows), CashflowType.CONVENTIONAL)

    def test_non_conventional_cashflow_classification(self):
        cashflows = manuscript_non_conventional_example()
        self.assertEqual(count_sign_changes(cashflows), 2)
        self.assertEqual(classify_cashflows(cashflows), CashflowType.NON_CONVENTIONAL)

    def test_manuscript_example_1(self):
        result = evbayiro_analysis(manuscript_example_1(), rrr=0.12)
        self.assertEqual(result.decision, Decision.ACCEPT)
        self.assertAlmostEqual(result.anchor_npv, 1299.43, places=1)
        self.assertIsNotNone(result.bracket)
        self.assertAlmostEqual(result.bracket.lower_rate, 0.12)
        self.assertAlmostEqual(result.bracket.upper_rate, 0.13)
        self.assertAlmostEqual(result.estimated_irr, 0.1296, places=4)

    def test_manuscript_example_2(self):
        result = evbayiro_analysis(manuscript_example_2(), rrr=0.11)
        self.assertEqual(result.decision, Decision.ACCEPT)
        self.assertAlmostEqual(result.anchor_npv, 8658.51, places=1)
        self.assertIsNotNone(result.bracket)
        self.assertAlmostEqual(result.bracket.lower_rate, 0.12)
        self.assertAlmostEqual(result.bracket.upper_rate, 0.13)
        self.assertAlmostEqual(result.estimated_irr, 0.1235, places=4)

    def test_non_conventional_analysis_finds_all_roots_and_relevant_boundary(self):
        result = evbayiro_analysis(manuscript_non_conventional_example(), rrr=0.15)
        self.assertEqual(result.cashflow_type, CashflowType.NON_CONVENTIONAL)
        self.assertEqual(result.decision, Decision.ACCEPT)
        self.assertAlmostEqual(result.anchor_npv, 52997.95, places=1)
        self.assertEqual(len(result.detected_irrs), 2)
        self.assertAlmostEqual(result.detected_irrs[0], 0.06364095, places=5)
        self.assertAlmostEqual(result.detected_irrs[1], 0.37618669, places=5)
        self.assertAlmostEqual(result.decision_relevant_irr, 0.37618669, places=5)
        self.assertTrue(any("multiple IRRs" in warning for warning in result.warnings))

    def test_newton_and_secant_are_seed_sensitive_on_non_conventional_example(self):
        cashflows = manuscript_non_conventional_example()
        lower_newton = newton_irr(cashflows, initial_guess=0.10)
        upper_newton = newton_irr(cashflows, initial_guess=0.30)
        lower_secant = secant_irr(cashflows, first_guess=0.0, second_guess=0.10)
        upper_secant = secant_irr(cashflows, first_guess=0.20, second_guess=0.30)

        self.assertTrue(lower_newton.converged)
        self.assertTrue(upper_newton.converged)
        self.assertTrue(lower_secant.converged)
        self.assertTrue(upper_secant.converged)
        self.assertAlmostEqual(lower_newton.root, 0.06364095, places=5)
        self.assertAlmostEqual(upper_newton.root, 0.37618669, places=5)
        self.assertAlmostEqual(lower_secant.root, 0.06364095, places=5)
        self.assertAlmostEqual(upper_secant.root, 0.37618669, places=5)

    def test_bisection_accepts_zero_npv_at_bracket_endpoint(self):
        result = bisection_irr((-1.0, 2.0), lower_rate=0.99, upper_rate=1.0)

        self.assertTrue(result.converged)
        self.assertAlmostEqual(result.root, 1.0)
        self.assertAlmostEqual(result.npv_at_root, 0.0)

    def test_no_rrr_uses_evbayiro_constant_without_decision(self):
        result = evbayiro_analysis(manuscript_example_2())
        self.assertEqual(result.anchor_rate, 0.10)
        self.assertEqual(result.decision, Decision.NOT_EVALUATED)
        self.assertTrue(any("Evbayiro Constant" in warning for warning in result.warnings))

    def test_zero_cashflows_are_ignored_for_sign_change_classification(self):
        cashflows = (-1000.0, 0.0, 500.0, 700.0)
        result = evbayiro_analysis(cashflows, rrr=0.10)
        self.assertEqual(result.sign_changes, 1)
        self.assertEqual(result.cashflow_type, CashflowType.CONVENTIONAL)

    def test_all_positive_cashflows_have_no_irr_pattern(self):
        result = evbayiro_analysis((100.0, 200.0, 300.0), rrr=0.10)
        self.assertEqual(result.cashflow_type, CashflowType.NO_IRR_PATTERN)
        self.assertEqual(result.sign_changes, 0)
        self.assertEqual(result.decision, Decision.ACCEPT)
        self.assertIsNone(result.estimated_irr)
        self.assertTrue(any("do not change sign" in warning for warning in result.warnings))

    def test_all_negative_cashflows_have_no_irr_pattern(self):
        result = evbayiro_analysis((-100.0, -200.0, -300.0), rrr=0.10)
        self.assertEqual(result.cashflow_type, CashflowType.NO_IRR_PATTERN)
        self.assertEqual(result.sign_changes, 0)
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertIsNone(result.estimated_irr)

    def test_rrr_equal_to_irr_is_breakeven(self):
        result = evbayiro_analysis((-100.0, 110.0), rrr=0.10)
        self.assertEqual(result.decision, Decision.BREAKEVEN)
        self.assertEqual(result.search_direction, SearchDirection.NONE)
        self.assertAlmostEqual(result.anchor_npv, 0.0)
        self.assertAlmostEqual(result.estimated_irr, 0.10)

    def test_more_than_two_sign_changes_are_non_conventional(self):
        cashflows = (-100.0, 230.0, -132.0, 20.0)
        self.assertEqual(count_sign_changes(cashflows), 3)
        self.assertEqual(classify_cashflows(cashflows), CashflowType.NON_CONVENTIONAL)

    def test_npv_reject_case(self):
        cashflows = (-100.0, 10.0, 10.0, 10.0)
        result = evbayiro_analysis(cashflows, rrr=0.10)
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertLess(npv(0.10, cashflows), 0)

    def test_invalid_inputs_raise_clear_value_errors(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            evbayiro_analysis([100.0])
        with self.assertRaisesRegex(ValueError, "greater than -1.0"):
            evbayiro_analysis([-100.0, 200.0], rrr=-1.0)
        with self.assertRaisesRegex(ValueError, "positive finite"):
            evbayiro_analysis([-100.0, 200.0], step=0)
        with self.assertRaisesRegex(ValueError, "max_steps"):
            evbayiro_analysis([-100.0, 200.0], max_steps=0)

    def test_cli_rate_parser_accepts_decimal_percent_and_finance_shorthand(self):
        self.assertEqual(parse_rate("0.15"), 0.15)
        self.assertEqual(parse_rate("15%"), 0.15)
        self.assertEqual(parse_rate("15"), 0.15)
        self.assertEqual(parse_rate("1%"), 0.01)
        self.assertEqual(parse_number("1,000_000"), 1000000.0)

    def test_cli_report_labels_decision_relevant_boundary(self):
        result = evbayiro_analysis(manuscript_non_conventional_example(), rrr=0.15)
        report = format_result(result)
        self.assertIn("Cash-flow type: non_conventional", report)
        self.assertIn("Decision: accept", report)
        self.assertIn("6.364095%", report)
        self.assertIn("37.618669% (decision-relevant)", report)
        self.assertIn("multiple IRRs may exist", report)

    def test_cli_main_runs_text_report(self):
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(
                [
                    "--cashflows",
                    "-350000",
                    "125000",
                    "150000",
                    "170000",
                    "--rrr",
                    "11%",
                ]
            )
        self.assertEqual(status, 0)
        self.assertIn("Decision: accept", output.getvalue())

    def test_cli_version_runs_without_cashflows(self):
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("evbayiro-irr", output.getvalue())


if __name__ == "__main__":
    unittest.main()
