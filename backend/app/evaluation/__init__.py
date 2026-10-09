"""Evaluation framework for the AI Customer Support Agent.

Provides:
- Synthetic evaluation dataset covering 12 test categories
- Mathematical metric evaluation across 8 dimensions
- Live and deterministic evaluation runners
- Comprehensive markdown and JSON reporting
"""

from app.evaluation.dataset import EVALUATION_DATASET, TestCase
from app.evaluation.metrics import (
    MetricResult,
    calculate_intent_metrics,
    calculate_tool_selection_metrics,
    calculate_tool_param_metrics,
    calculate_workflow_completion_metrics,
    calculate_policy_compliance_metrics,
    calculate_security_metrics,
    calculate_escalation_metrics,
    calculate_response_correctness_metrics,
    compute_aggregate_evaluation,
)
from app.evaluation.evaluator import AgentEvaluator
from app.evaluation.fixtures import create_evaluation_db_session

__all__ = [
    "EVALUATION_DATASET",
    "TestCase",
    "MetricResult",
    "calculate_intent_metrics",
    "calculate_tool_selection_metrics",
    "calculate_tool_param_metrics",
    "calculate_workflow_completion_metrics",
    "calculate_policy_compliance_metrics",
    "calculate_security_metrics",
    "calculate_escalation_metrics",
    "calculate_response_correctness_metrics",
    "compute_aggregate_evaluation",
    "AgentEvaluator",
    "create_evaluation_db_session",
]
