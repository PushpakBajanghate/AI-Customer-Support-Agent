"""LangGraph Support Agent: real-time database context inspection and dynamic AI reasoning."""

import logging
import re
from datetime import datetime, timedelta, timezone

from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.state import AgentState
from app.services.llm import get_llm, _extract_content_text
from app.agents.support_tools import (
    get_customer_information,
    get_recent_orders,
    get_order_items,
    get_shipments,
    get_returns,
    get_refunds,
    get_support_tickets,
)

logger = logging.getLogger(__name__)


def support_agent_node(state: AgentState) -> AgentState:
    """Grounds support responses in real PostgreSQL records and invokes Gemini dynamically."""
    db = state.get("db_session")
    if db is None:
        return {**state, "final_response": "I cannot access your support records right now. Please try again shortly."}

    customer_id = state["customer_id"]
    customer_name = state.get("customer_name") or "Valued Customer"
    customer_email = state.get("customer_email") or ""
    intent = state.get("intent") or "UNKNOWN"
    confidence = state.get("confidence") or 0.8
    message = state["message"]
    history = state.get("conversation_history", [])

    # Load real database records
    orders = get_recent_orders(db, customer_id, limit=8)
    shipments = get_shipments(db, customer_id)
    returns = get_returns(db, customer_id)
    refunds = get_refunds(db, customer_id)
    tickets = get_support_tickets(db, customer_id)

    # Attach shipments to their respective orders
    shipments_by_order = {s["order_id"]: s for s in shipments}

    context = {
        "customer": {"id": customer_id, "name": customer_name, "email": customer_email},
        "orders": orders,
        "shipments": shipments,
        "returns": returns,
        "refunds": refunds,
        "tickets": tickets,
    }

    order_id = _referenced_order_id(message, orders, history)
    target_order = next((o for o in orders if o["id"] == order_id), None) if order_id else None

    # Handle state mutations (cancellation, returns, refunds, human escalations)
    if intent == "ORDER_CANCEL":
        # If there's an unambiguous target order, check if eligible for cancellation
        if target_order:
            if target_order["status"].lower() == "processing":
                state = {
                    **state,
                    "support_context": context,
                    "requested_action": {"type": "cancel_order", "order_id": target_order["id"]},
                }
                # Supervisor gate will handle confirmation/execution
                return state
        elif len(orders) == 1 and orders[0]["status"].lower() == "processing":
            state = {
                **state,
                "support_context": context,
                "requested_action": {"type": "cancel_order", "order_id": orders[0]["id"]},
            }
            return state

    has_specific_product_query = bool({
        _normalise(word) for word in re.findall(r"[\w-]+", message.lower())
        if _normalise(word) not in {"i", "me", "my", "a", "an", "the", "want", "to", "return", "replace", "received", "wrong", "damaged", "item", "product", "one", "from", "yesterday", "today", "order", "can", "please", "help"} and len(word) > 2
    })

    if intent in {"ORDER_RETURN", "DAMAGED_PRODUCT", "WRONG_PRODUCT"}:
        matches = _matching_orders(message, orders)
        if target_order:
            matches = [target_order]
        elif not matches and not has_specific_product_query and len(orders) == 1:
            matches = orders

        if len(matches) == 1 and matches[0]["status"].lower() == "delivered":
            selected = matches[0]
            items = get_order_items(db, customer_id, selected["id"])
            if items:
                state = {
                    **state,
                    "support_context": context,
                    "requested_action": {
                        "type": "create_return",
                        "order_id": selected["id"],
                        "order_item_id": items[0]["id"],
                        "reason": _reason_from_message(message) or "Customer requested return",
                    },
                }
                return state

    if intent == "REFUND_REQUEST":
        if target_order:
            state = {
                **state,
                "support_context": context,
                "requested_action": {"type": "create_refund", "order_id": target_order["id"]},
            }
            return state

    if intent == "HUMAN_ESCALATION":
        state = {
            **state,
            "support_context": context,
            "requested_action": {
                "type": "create_support_ticket",
                "subject": message[:120],
                "description": message,
                "priority": "high",
            },
        }
        return state

    # Format real database records into structured text for Gemini LLM
    db_summary_lines = []
    if not orders:
        db_summary_lines.append("No orders currently found for this customer account.")
    else:
        for o in orders:
            item_desc = ", ".join(
                f"{it['product_name']} (Qty: {it['quantity']}, ${it['price']:.2f}, Return Window: {it.get('return_window_days', 14)} days, Warranty: {it.get('warranty_days', 365)} days)"
                for it in o.get("items", [])
            )
            ship = shipments_by_order.get(o["id"])
            ship_desc = (
                f"Carrier: {ship['carrier']}, Tracking #: {ship['tracking_number']}, Status: {ship['status']}, Est Delivery: {ship.get('estimated_delivery') or 'N/A'}"
                if ship else "No separate shipment details recorded (Processing/In-house fulfillment)"
            )
            db_summary_lines.append(
                f"- Order #{o['id']}: Placed {str(o.get('order_date', ''))[:10]} | Status: {o['status'].upper()} | Total: ${float(o.get('total_amount', 0)):.2f}\n"
                f"  Items: {item_desc}\n"
                f"  Shipment: {ship_desc}"
            )

    if returns:
        db_summary_lines.append("\nCustomer Return Records:")
        for r in returns:
            db_summary_lines.append(f"- Return on Order #{r['order_id']}: Status: {r['status']}, Reason: {r['reason']}")

    if refunds:
        db_summary_lines.append("\nCustomer Refund Records:")
        for rf in refunds:
            db_summary_lines.append(f"- Refund on Order #{rf['order_id']}: ${float(rf['amount']):.2f}, Status: {rf['status']}")

    database_records_text = "\n".join(db_summary_lines)

    # Policy knowledge context (from RAG)
    knowledge = state.get("knowledge_context") or []
    policy_text = "\n\n".join(
        f"[{k.get('title', k.get('source', 'Policy'))}]: {k.get('content', '')[:600]}"
        for k in knowledge
    ) or "Standard Store Policy: 14-day return window for delivered items in original packaging. Cancellations permitted only while status is 'Processing'."

    # History formatting
    history_text = "\n".join(
        f"{h.get('role', 'user').capitalize()}: {h.get('content', '')}"
        for h in history[-6:]
    ) or "(New conversation)"

    support_system_prompt = f"""You are SupportAI, an intelligent, empathetic, and factual customer support specialist.
You are communicating in real time with authenticated customer: {customer_name} (Email: {customer_email}, ID: #{customer_id}).

ACTUAL POSTGRESQL DATABASE RECORDS FOR THIS CUSTOMER:
{database_records_text}

OFFICIAL COMPANY POLICY KNOWLEDGE (RETRIEVED VIA RAG):
{policy_text}

CONVERSATION HISTORY:
{history_text}

CLASSIFIED INTENT: {intent} (Confidence: {confidence:.0%})

STRICT GROUNDING & VERIFICATION INSTRUCTIONS:
1. Ground your response 100% in the real customer orders and official policy documents above. Never fabricate data or assume orders that do not exist.
2. REAL-TIME ITEM & ORDER VERIFICATION:
   - When the customer asks to return, cancel, track, replace, or inquire about any product or order:
   - Check the ACTUAL POSTGRESQL DATABASE RECORDS above in real-time.
   - If the customer does NOT have an order for that product name or order number in their database records:
     * Inform the customer clearly and politely that you searched their account records in real-time and there is no order under that name or order ID found on their account.
     * List the actual orders and items they DO currently have on their account so they can verify.
     * Cite the relevant policy from the OFFICIAL COMPANY POLICY KNOWLEDGE above (e.g. store return window conditions, resalable packaging rules, or cancellation policies) to explain how policies apply.
     * Do NOT escalate to a human representative simply because the customer asked about an unpurchased item.
3. FOR ORDERS/ITEMS FOUND IN DATABASE RECORDS:
   - Order Status / Tracking: State Order ID, product name, status, carrier name, tracking code, and delivery estimate.
   - Return Requests: Check if the order status is 'DELIVERED'.
     * If delivered within the product's return window days: explain the return process and policy requirements (original packaging, resalable condition).
     * If delivered beyond the return window days: explain empathetically that the delivery date exceeds the store return window under company policy, and mention warranty coverage if applicable.
   - Cancellations:
     * If status is 'PROCESSING': offer cancellation and request their confirmation.
     * If status is 'SHIPPED' or 'DELIVERED': explain that in-transit or delivered orders cannot be cancelled mid-delivery per shipping/cancellation policy, but can be returned once received.
   - Policy / Warranty Inquiries: Fully review and cite the relevant policy from the OFFICIAL COMPANY POLICY KNOWLEDGE above.
4. Be polite, concise, professional, and conversational.
"""

    try:
        llm = get_llm()
        ai_msg = llm.invoke([
            SystemMessage(content=support_system_prompt),
            HumanMessage(content=message)
        ])
        final_text = _extract_content_text(ai_msg.content)
    except Exception as exc:
        logger.error(f"Failed to generate support response with LLM: {exc}")
        # Graceful fallback that still references real database orders
        if orders:
            order_summaries = "; ".join(f"Order #{o['id']} ({o['status']})" for o in orders)
            final_text = f"I've retrieved your account details. You currently have: {order_summaries}. How can I assist you with this?"
        else:
            final_text = "I've checked your account, but there are no active orders placed yet. How else can I help you today?"

    return {
        **state,
        "support_context": context,
        "final_response": final_text,
    }


def _matching_orders(message: str, orders: list[dict]) -> list[dict]:
    words = {_normalise(word) for word in re.findall(r"[\w-]+", message.lower())}
    ignored = {"i", "me", "my", "a", "an", "the", "want", "to", "return", "replace", "received", "wrong", "damaged", "item", "product", "one", "from", "yesterday", "today", "order", "can"}
    terms = {word for word in words if word not in ignored and len(word) > 2}
    if not terms:
        return orders
    matches = []
    for order in orders:
        searchable = {_normalise(x) for item in order.get("items", []) for x in (item.get("product_name", ""), item.get("category", ""))}
        if any(term in token or token in term for term in terms for token in searchable):
            matches.append(order)
    return matches


def _mentioned_order_id(message: str, orders: list[dict]) -> int | None:
    ids = {int(value) for value in re.findall(r"(?:order\s*#?\s*|#)(\d+)", message.lower())}
    for order in orders:
        if order["id"] in ids:
            return order["id"]
    return None


def _referenced_order_id(message: str, orders: list[dict], history: list[dict]) -> int | None:
    direct = _mentioned_order_id(message, orders)
    if direct:
        return direct
    if re.search(r"\b(that|this|the one|it)\b", message.lower()):
        for turn in reversed(history):
            previous = _mentioned_order_id(str(turn.get("content", "")), orders)
            if previous:
                return previous
    # If customer has only 1 order in total, associate it directly
    if len(orders) == 1:
        return orders[0]["id"]
    return None


def _normalise(value: str) -> str:
    value = re.sub(r"[^a-z0-9]", "", value.lower())
    return value[:-1] if value.endswith("s") else value


def _reason_from_message(message: str) -> str | None:
    match = re.search(r"(?:because|reason is|reason:)\s+(.+)", message, re.IGNORECASE)
    return match.group(1).strip() if match else None
