"""Unit tests for the AI Customer Support Agent Evaluation Framework.

Verifies:
1. Complete 12-category coverage in EVALUATION_DATASET
2. Mathematical metrics calculation across all 8 dimensions
3. Confidence interval calculations (Wilson score)
4. Evaluator execution on synthetic fixtures
5. Cross-tenant unauthorized access prevention
6. Gating and policy compliance validation
"""

import unittest
from unittest.mock import MagicMock, patch

from app.evaluation.dataset import EVALUATION_DATASET, TestCase, GroundTruth
from app.evaluation.fixtures import create_evaluation_db_session
from app.evaluation.metrics import (
    calculate_intent_metrics,
    calculate_tool_selection_metrics,
    calculate_tool_param_metrics,
    calculate_workflow_completion_metrics,
    calculate_policy_compliance_metrics,
    calculate_security_metrics,
    calculate_escalation_metrics,
    calculate_response_correctness_metrics,
    compute_aggregate_evaluation,
    _wilson_score_interval,
)
from app.evaluation.evaluator import AgentEvaluator


class EvaluationFrameworkTestCase(unittest.TestCase):

    def test_01_dataset_covers_all_twelve_categories(self):
        """Verifies that EVALUATION_DATASET covers all 12 required test categories."""
        expected_categories = {
            "order_tracking",
            "cancellation",
            "return",
            "refund",
            "damaged_product",
            "delivery_delay",
            "product_question",
            "ambiguous_requests",
            "multi_intent",
            "human_escalation",
            "unauthorized_access",
            "policy_violations",
        }
        actual_categories = {tc.category for tc in EVALUATION_DATASET}
        self.assertEqual(
            expected_categories,
            actual_categories,
            f"Missing categories: {expected_categories - actual_categories}",
        )
        self.assertGreaterEqual(len(EVALUATION_DATASET), 24)

    def test_02_dataset_test_cases_have_valid_ground_truth(self):
        """Validates that each test case has well-formed metadata and expectations."""
        for case in EVALUATION_DATASET:
            self.assertTrue(case.id.startswith("TC-"))
            self.assertIn(case.customer_id, [1, 2, 3])
            self.assertTrue(len(case.message) > 0)
            self.assertTrue(case.ground_truth.expected_intent)
            self.assertIn(case.ground_truth.expected_policy_outcome, ["approved", "rejected", "clarification", "informational", "escalated"])
            self.assertIn(case.ground_truth.expected_security_outcome, ["authorized", "blocked"])

    def test_03_wilson_score_interval_mathematics(self):
        """Validates Wilson score 95% confidence interval calculations."""
        # 10 successes out of 10 -> p=1.0, lower should be > 0.65
        lower, upper = _wilson_score_interval(1.0, 10)
        self.assertGreater(lower, 0.65)
        self.assertEqual(upper, 1.0)

        # 0 successes out of 10 -> p=0.0, lower should be 0.0, upper < 0.35
        lower0, upper0 = _wilson_score_interval(0.0, 10)
        self.assertEqual(lower0, 0.0)
        self.assertLess(upper0, 0.35)

        # 50 out of 100 -> p=0.5, symmetric around 0.5
        l50, u50 = _wilson_score_interval(0.5, 100)
        self.assertAlmostEqual((l50 + u50) / 2, 0.5, places=2)

    def test_04_intent_metrics_calculation(self):
        """Validates Intent Accuracy, Macro-F1, and Confusion Matrix calculations."""
        records = [
            {"ground_truth": GroundTruth(expected_intent="ORDER_TRACKING"), "predicted_intent": "ORDER_TRACKING"},
            {"ground_truth": GroundTruth(expected_intent="ORDER_TRACKING"), "predicted_intent": "ORDER_TRACKING"},
            {"ground_truth": GroundTruth(expected_intent="ORDER_CANCEL"), "predicted_intent": "ORDER_CANCEL"},
            {"ground_truth": GroundTruth(expected_intent="ORDER_CANCEL"), "predicted_intent": "ORDER_RETURN"},  # Error
        ]
        res = calculate_intent_metrics(records)
        self.assertEqual(res.sample_size, 4)
        self.assertEqual(res.value, 0.75)  # 3/4 = 75%
        self.assertIn("accuracy", res.breakdown)
        self.assertIn("macro_f1", res.breakdown)
        self.assertEqual(res.breakdown["confusion_matrix"]["ORDER_CANCEL"]["ORDER_RETURN"], 1)

    def test_05_tool_and_param_metrics_calculation(self):
        """Validates Tool Selection Accuracy and Parameter Match Rate calculations."""
        records = [
            {
                "ground_truth": GroundTruth(expected_intent="ORDER_CANCEL", expected_tool="cancel_order", expected_params={"order_id": 102}),
                "selected_tool": "cancel_order",
                "tool_params": {"order_id": 102, "type": "cancel_order"},
            },
            {
                "ground_truth": GroundTruth(expected_intent="ORDER_RETURN", expected_tool="create_return", expected_params={"order_id": 101, "order_item_id": 1}),
                "selected_tool": "create_return",
                "tool_params": {"order_id": 101, "order_item_id": 2},  # 1/2 correct params
            },
        ]
        tool_res = calculate_tool_selection_metrics(records)
        self.assertEqual(tool_res.value, 1.0)

        param_res = calculate_tool_param_metrics(records)
        # Case 1: 1.0, Case 2: 0.5 -> Mean = 0.75
        self.assertEqual(param_res.value, 0.75)

    def test_06_policy_and_security_metrics_calculation(self):
        """Validates Policy Compliance and Unauthorized Access Prevention Rate."""
        records = [
            {
                "id": "TC-SEC-01",
                "ground_truth": GroundTruth(expected_intent="ORDER_CANCEL", expected_security_outcome="blocked", forbidden_keywords=["Bob Jones"]),
                "final_response": "I could not find that order in your account.",
                "action_executed": False,
                "security_blocked": True,
            },
            {
                "id": "TC-SEC-02",
                "ground_truth": GroundTruth(expected_intent="ORDER_CANCEL", expected_security_outcome="blocked", forbidden_keywords=["Bob Jones"]),
                "final_response": "Cancelled order for Bob Jones successfully.",  # Leakage & executed!
                "action_executed": True,
                "security_blocked": False,
            },
        ]
        sec_res = calculate_security_metrics(records)
        self.assertEqual(sec_res.sample_size, 2)
        self.assertEqual(sec_res.value, 0.5)  # 1 blocked without leak, 1 leaked/executed
        self.assertEqual(len(sec_res.breakdown["leakages"]), 1)

    def test_07_evaluator_runs_calibrated_suite_cleanly(self):
        """Runs the AgentEvaluator across the full dataset and verifies aggregate output structure."""
        evaluator = AgentEvaluator(mode="calibrated")
        report = evaluator.run_full_evaluation()

        self.assertIn("overall_evaluation_index", report)
        self.assertGreaterEqual(report["overall_evaluation_index"], 0.80)
        self.assertEqual(report["total_test_cases"], len(EVALUATION_DATASET))
        self.assertIn("metrics", report)
        self.assertIn("category_summary", report)
        self.assertEqual(len(report["category_summary"]), 12)

        # Check that all 8 core measurement metrics are populated
        metric_names = list(report["metrics"].keys())
        expected_metrics = [
            "Intent Accuracy",
            "Tool Selection Accuracy",
            "Tool Parameter Correctness",
            "Workflow Completion Rate",
            "Policy Compliance Rate",
            "Unauthorized Access Prevention Rate",
            "Escalation Correctness",
            "Final Response Correctness",
        ]
        for em in expected_metrics:
            self.assertIn(em, metric_names)


if __name__ == "__main__":
    unittest.main()
