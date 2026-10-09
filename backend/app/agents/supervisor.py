"""Lightweight safety gate for state-changing support actions."""

import re

from app.agents.state import AgentState
from app.tools.support import (
    cancel_order,
    check_return_eligibility,
    create_refund,
    create_return,
    create_support_ticket,
    get_customer_orders,
    get_order,
)
from app.agents.support_tools import get_customer_information


SENSITIVE_ACTIONS = {"cancel_order", "create_return", "create_refund", "create_support_ticket"}


def supervisor_node(state: AgentState) -> AgentState:
    """Validate and, only after confirmation, execute a requested action."""
    action = state.get("requested_action")
    if not action or action.get("type") not in SENSITIVE_ACTIONS:
        return {**state, "supervisor_result": None}

    db = state.get("db_session")
    customer_id = state.get("customer_id")
    if not db or not customer_id or not get_customer_information(db, customer_id):
        return _rejected(state, "AUTHENTICATION_REQUIRED", "I could not verify your customer account for this action.")

    action_type = action["type"]
    order_id = action.get("order_id")
    if action_type in {"cancel_order", "create_return", "create_refund"}:
        ownership = get_order(order_id, customer_id, db=db)
        if not ownership.get("ok"):
            return _rejected(state, "ORDER_NOT_FOUND", "I could not find that order in your account.")

    if not _is_confirmed(state):
        return _rejected(state, "CONFIRMATION_REQUIRED", _confirmation_prompt(action_type, order_id))

    if action_type == "cancel_order":
        result = cancel_order(order_id, customer_id, db=db)
    elif action_type == "create_return":
        eligibility = check_return_eligibility(order_id, action["order_item_id"], customer_id, db=db)
        if not eligibility.get("ok") or not eligibility.get("data", {}).get("eligible"):
            return _rejected(state, eligibility.get("error", "RETURN_NOT_ELIGIBLE"), "That item is not eligible for a return.")
        reason = action.get("reason") or _reason_from_history(state)
        if not reason:
            return _rejected(state, "RETURN_REASON_REQUIRED", "Please provide the reason for the return before I submit it.")
        result = create_return(order_id, action["order_item_id"], reason, customer_id, db=db)
    elif action_type == "create_refund":
        result = create_refund(order_id, customer_id, db=db)
    else:
        result = create_support_ticket(customer_id, action["subject"], action["description"], db=db)

    if not result.get("ok"):
        return _rejected(state, result.get("error", "ACTION_REJECTED"), "I could not complete that request after validation.")
    return {
        **state,
        "supervisor_result": {"status": "approved", "action": action_type, "tool_result": result},
        "final_response": _success_message(action_type, result),
    }


def _rejected(state: AgentState, reason: str, response: str) -> AgentState:
    return {**state, "supervisor_result": {"status": "rejected", "reason": reason}, "final_response": response}


def _is_confirmed(state: AgentState) -> bool:
    message = state.get("message", "").strip().lower()
    return bool(re.search(r"\b(confirm|confirmed|yes|go ahead|do it|proceed)\b", message))


def _reason_from_history(state: AgentState) -> str | None:
    for turn in reversed(state.get("conversation_history", [])):
        text = str(turn.get("content", ""))
        match = re.search(r"(?:because|reason is|reason:)\s+(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _confirmation_prompt(action_type: str, order_id: int | None) -> str:
    target = f" for order #{order_id}" if order_id else ""
    action = {"cancel_order": "cancel the order", "create_return": "submit the return", "create_refund": "request the refund", "create_support_ticket": "create the support ticket"}[action_type]
    return f"I have validated the request{target}. Please confirm if you want me to {action}."


def _success_message(action_type: str, result: dict) -> str:
    labels = {"cancel_order": "cancellation", "create_return": "return request", "create_refund": "refund request", "create_support_ticket": "support ticket"}
    identifier = result.get("data", {}).get("id")
    suffix = f" #{identifier}" if identifier else ""
    return f"Your {labels[action_type]}{suffix} was submitted successfully after validation."
