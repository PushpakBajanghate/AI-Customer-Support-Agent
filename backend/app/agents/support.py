"""LangGraph Support Agent: context inspection and safe next-step decisions."""

import re
from datetime import datetime, timezone

from app.agents.state import AgentState
from app.agents.support_tools import (
    get_customer_information, get_recent_orders, get_order_items, get_shipments,
    get_returns, get_refunds, get_support_tickets,
)


def support_agent_node(state: AgentState) -> AgentState:
    """Use approved read tools, then produce a verified response.

    The node deliberately does not expose a write tool.  It selects records
    from database results and asks for clarification only when selection is
    ambiguous.
    """
    db = state.get("db_session")
    if db is None:
        return {**state, "final_response": "I cannot access your support records right now. Please try again shortly."}

    customer_id = state["customer_id"]
    intent = state.get("intent") or "UNKNOWN"
    message = state["message"]
    customer = get_customer_information(db, customer_id)
    orders = get_recent_orders(db, customer_id)
    context = {"customer": customer, "orders": orders}

    order_id = _mentioned_order_id(message, orders)
    if intent in {"ORDER_RETURN", "DAMAGED_PRODUCT", "WRONG_PRODUCT"}:
        matches = _matching_orders(message, orders)
        if order_id:
            matches = [order for order in orders if order["id"] == order_id]
        if len(matches) == 1:
            selected = matches[0]
            context.update({"items": get_order_items(db, customer_id, selected["id"]),
                            "returns": get_returns(db, customer_id, selected["id"])})
            state = {**state, "support_context": context}
            return {**state, "final_response": _single_order_response(selected, intent, context["returns"])}
        if len(matches) > 1:
            state = {**state, "support_context": context}
            return {**state, "final_response": _multiple_order_response(matches, intent)}
        return {**state, "support_context": context,
                "final_response": "I checked your recent orders but could not find an item matching that description. What product would you like help with?"}

    if intent in {"ORDER_TRACKING", "DELIVERY_DELAY"}:
        shipments = get_shipments(db, customer_id, order_id)
        context["shipments"] = shipments
        if not shipments:
            response = "I checked your recent orders, but I could not find a shipment to track. Which order would you like me to check?"
        else:
            response = "I checked your shipment records. " + "; ".join(
                f"Order #{s['order_id']} is {s['status']} with {s['carrier']} (tracking {s['tracking_number']})."
                for s in shipments
            )
        return {**state, "support_context": context, "final_response": response}

    if intent in {"REFUND_STATUS", "REFUND_REQUEST"}:
        refunds = get_refunds(db, customer_id, order_id)
        context["refunds"] = refunds
        response = ("I checked your refund records, but found none for your account."
                    if not refunds else "I checked your refund records. " + "; ".join(
                        f"Order #{r['order_id']}: {r['status']} for {r['amount']}." for r in refunds))
        return {**state, "support_context": context, "final_response": response}

    context["tickets"] = get_support_tickets(db, customer_id)
    return {**state, "support_context": context, "final_response": state.get("router_response") or "I’m checking your support records now. Please tell me what you need help with."}


def _matching_orders(message: str, orders: list[dict]) -> list[dict]:
    words = {_normalise(word) for word in re.findall(r"[\w-]+", message.lower())}
    ignored = {"i", "me", "my", "a", "an", "the", "want", "to", "return", "replace", "received", "wrong", "damaged", "item", "product"}
    terms = {word for word in words if word not in ignored and len(word) > 2}
    if not terms:
        return orders
    matches = []
    for order in orders:
        searchable = {_normalise(x) for item in order["items"] for x in (item["product_name"], item["category"])}
        if any(term in token or token in term for term in terms for token in searchable):
            matches.append(order)
    return matches


def _mentioned_order_id(message: str, orders: list[dict]) -> int | None:
    ids = {int(value) for value in re.findall(r"(?:order\s*#?\s*|#)(\d+)", message.lower())}
    for order in orders:
        if order["id"] in ids:
            return order["id"]
    return None


def _normalise(value: str) -> str:
    value = re.sub(r"[^a-z0-9]", "", value.lower())
    return value[:-1] if value.endswith("s") else value


def _single_order_response(order: dict, intent: str, returns: list[dict]) -> str:
    item_names = ", ".join(item["product_name"] for item in order["items"])
    prior = " This order already has a return record, so I will not create another request." if returns else ""
    action = "return" if intent == "ORDER_RETURN" else "resolve this issue with"
    return f"I found one matching order: #{order['id']} ({item_names}), placed on {order['order_date'][:10]}. I’ll use this order for your {action} request.{prior}"


def _multiple_order_response(orders: list[dict], intent: str) -> str:
    lines = [f"#{order['id']} — {', '.join(item['product_name'] for item in order['items'])}, placed {order['order_date'][:10]}, status {order['status']}" for order in orders]
    return "I found multiple matching orders:\n" + "\n".join(lines) + "\nWhich one would you like me to use?"

