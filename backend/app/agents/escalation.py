"""Small, deterministic escalation decision node."""

import re

from app.agents.state import AgentState


def escalation_needed(state: AgentState) -> bool:
    message = state.get("message", "").lower()
    intent = state.get("intent")
    confidence = state.get("confidence") or 0.0
    history = state.get("conversation_history", [])
    failure_count = int(state.get("tool_failures", 0) or 0)
    failure_count += sum(
        1 for turn in history
        if (
            turn.get("role") == "tool" and re.search(r"failed|failure|unavailable|error", str(turn.get("content", "")), re.I)
        ) or (
            turn.get("role") == "assistant" and "could not complete that request" in str(turn.get("content", "")).lower()
        )
    )

    explicit_human = bool(re.search(r"\b(human|representative|live agent|support agent|person)\b", message))
    fraud = bool(re.search(r"\b(fraud|fraudulent|unauthorized|not mine|stolen|scam|chargeback)\b", message))
    policy_exception = bool(re.search(r"\b(exception|override|outside the policy|extend the return|waive)\b", message))
    payment_ambiguous = intent == "PAYMENT_ISSUE" or (
        "payment" in message and bool(re.search(r"\b(unclear|ambiguous|unknown|pending|missing|charged twice)\b", message))
    )
    unsupported = intent == "UNKNOWN" or confidence < 0.55 or bool(state.get("needs_clarification"))
    return explicit_human or fraud or policy_exception or failure_count >= 2 or payment_ambiguous or unsupported


def escalation_node(state: AgentState) -> AgentState:
    message = state.get("message", "")
    reason = _reason(state)
    priority = "urgent" if reason in {"fraud_suspected", "payment_ambiguous"} else "high" if reason in {"human_requested", "policy_exception"} else "medium"
    action = {
        "type": "create_support_ticket",
        "requires_confirmation": False,
        "subject": message[:120] or reason,
        "description": message,
        "issue": reason,
        "summary": message,
        "priority": priority,
    }
    return {**state, "requested_action": action, "escalation_reason": reason, "escalation_priority": priority}


def _reason(state: AgentState) -> str:
    message = state.get("message", "").lower()
    if re.search(r"\b(fraud|fraudulent|unauthorized|not mine|stolen|scam|chargeback)\b", message):
        return "fraud_suspected"
    if re.search(r"\b(exception|override|outside the policy|extend the return|waive)\b", message):
        return "policy_exception"
    if state.get("intent") == "PAYMENT_ISSUE" or ("payment" in message and re.search(r"\b(unclear|ambiguous|unknown|pending|missing|charged twice)\b", message)):
        return "payment_ambiguous"
    if re.search(r"\b(human|representative|live agent|support agent|person)\b", message):
        return "human_requested"
    if int(state.get("tool_failures", 0) or 0) >= 2:
        return "repeated_tool_failures"
    if state.get("intent") == "UNKNOWN" or (state.get("confidence") or 0.0) < 0.55:
        return "unsupported_request"
    return "unable_to_resolve"
