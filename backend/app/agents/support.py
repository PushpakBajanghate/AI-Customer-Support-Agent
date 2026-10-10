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

    # Handle state mutations ONLY when the user explicitly requests an action:
    # 1. ORDER_CANCEL: Only propose cancellation if user explicitly requests to cancel an order
    is_explicit_cancel = bool(re.search(r"\b(cancel|cancellation|stop order)\b", message, re.IGNORECASE))
    if intent == "ORDER_CANCEL" and is_explicit_cancel:
        if target_order and target_order["status"].lower() == "processing":
            state = {
                **state,
                "support_context": context,
                "requested_action": {"type": "cancel_order", "order_id": target_order["id"]},
            }
            return state
        elif not target_order and len(orders) == 1 and orders[0]["status"].lower() == "processing":
            state = {
                **state,
                "support_context": context,
                "requested_action": {"type": "cancel_order", "order_id": orders[0]["id"]},
            }
            return state

    # 2. ORDER_RETURN: Only trigger automated return creation if the user explicitly requests a return/refund
    # and NOT for general inquiries, technical issues, service/check visits, or complaints about prior responses
    is_explicit_return_request = bool(
        re.search(r"\b(want to return|initiate return|start return|return this|create return|send back|return request)\b", message, re.IGNORECASE)
    )
    is_service_or_defect_query = bool(
        re.search(r"\b(visit|check|technician|inspection|repair|fix|glitch|screen|display|flicker|not working|broken|warranty)\b", message, re.IGNORECASE)
    )

    if intent == "ORDER_RETURN" and is_explicit_return_request and not is_service_or_defect_query:
        matches = _matching_orders(message, orders)
        if target_order:
            matches = [target_order]
        elif not matches and len(orders) == 1:
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

    # 3. REFUND_REQUEST: Only if explicitly asking for refund processing
    is_explicit_refund = bool(re.search(r"\b(process refund|issue refund|give my money back|refund request)\b", message, re.IGNORECASE))
    if intent == "REFUND_REQUEST" and is_explicit_refund and target_order:
        state = {
            **state,
            "support_context": context,
            "requested_action": {"type": "create_refund", "order_id": target_order["id"]},
        }
        return state

    # 4. HUMAN_ESCALATION: Only if explicit agent requested
    if intent == "HUMAN_ESCALATION" and bool(re.search(r"\b(human|representative|live agent|person|supervisor)\b", message, re.IGNORECASE)):
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

    # History formatting: provide full recent context (up to 10 turns) so agent retains context across turns
    history_text = "\n".join(
        f"{h.get('role', 'user').capitalize()}: {h.get('content', '')}"
        for h in history[-10:]
    ) or "(New conversation)"

    support_system_prompt = f"""You are SupportAI, an intelligent, empathetic, fact-grounded customer support specialist.
You are communicating in real time with authenticated customer: {customer_name} (Email: {customer_email}, ID: #{customer_id}).

ACTUAL POSTGRESQL DATABASE RECORDS FOR THIS CUSTOMER:
{database_records_text}

OFFICIAL COMPANY POLICY KNOWLEDGE (RETRIEVED VIA RAG):
{policy_text}

CONVERSATION HISTORY (PAST TURNS IN THIS SESSION):
{history_text}

CURRENT CUSTOMER MESSAGE:
{message}

CLASSIFIED INTENT: {intent} (Confidence: {confidence:.0%})

STRICT MULTI-TURN CONVERSATION MEMORY & GROUNDING INSTRUCTIONS:
1. CONVERSATIONAL MEMORY & CONTEXT RESOLUTION:
   - Carefully review the CONVERSATION HISTORY to track the ongoing context and what product or topic was being discussed.
   - For example, if a previous message discussed a TV, monitor, or display (such as the UltraView Monitor), and the customer follows up with "i am having a glitch in the screen of tv and want to request a check visit help me" or refers to "it", understand that they are referring to the product discussed in context.
   - If the customer corrects you (e.g. "I was talking about the TV, why are you showing me another order?"), acknowledge the correction immediately with an apology, pivot to the correct product/order from their database records, and address their actual concern directly.
   - Do NOT repeat past rejected actions or canned refusal messages from previous turns. Answer their current query fresh and accurately in real time.

2. REAL-TIME ITEM & ORDER VERIFICATION:
   - When the customer asks about any item, product, or order number:
   - Check the ACTUAL POSTGRESQL DATABASE RECORDS above in real-time.
   - If the customer does NOT have an order for that item on their account (e.g. Saree, jacket, etc.):
     * Inform the customer clearly and politely that you searched their account records in real-time and there is no order under that name found on their account.
     * List the actual orders and items they DO currently have on their account so they can verify.
     * Cite the relevant policy from OFFICIAL COMPANY POLICY KNOWLEDGE (e.g. return window, packaging requirements) to explain standard rules.
     * Do NOT escalate to a human representative simply because an unpurchased item was mentioned.

3. HARDWARE DEFECTS, GLITCHES, AND SERVICE / CHECK VISITS:
   - If the customer reports a technical issue (e.g., glitch, screen lines, hardware defect) or requests a technician / check visit:
   - Correlate the issue with the relevant product in their orders (e.g. UltraView 27-inch 4K IPS Monitor, Order #33).
   - Check the product's WARRANTY coverage in their database record (e.g., 730 days warranty coverage).
   - Empathize with the defect, confirm that their item is well within its active warranty period, explain the warranty coverage, and offer next steps to schedule a service visit or inspection ticket rather than treating it as an expired return.

4. RETURN AND CANCELLATION REQUESTS:
   - Return requests: Check if the order is DELIVERED. If within the return window days, guide them through return steps. If past the return window days, explain politely citing policy and mention warranty if applicable.
   - Cancellation requests: If status is 'PROCESSING', offer cancellation. If 'SHIPPED' or 'DELIVERED', explain that shipped orders cannot be cancelled mid-transit.

5. Tone & Style:
   - Professional, empathetic, direct, and conversational.
   - Never hallucinate non-existent items, and never confuse one order with another.
"""

    final_text = None
    try:
        llm = get_llm(timeout=15)
        ai_msg = llm.invoke([
            SystemMessage(content=support_system_prompt),
            HumanMessage(content=message)
        ])
        final_text = _extract_content_text(ai_msg.content)
    except Exception as exc:
        logger.warning(f"Support agent primary LLM call encountered {exc}, attempting fast secondary call...")
        try:
            fallback_llm = get_llm(model_override="gemini-3.5-flash", timeout=8)
            ai_msg = fallback_llm.invoke([
                SystemMessage(content=support_system_prompt),
                HumanMessage(content=message)
            ])
            final_text = _extract_content_text(ai_msg.content)
        except Exception as fallback_exc:
            logger.error(f"Failed to generate support response with LLM: {fallback_exc}")
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
    """Finds orders whose item names or categories match words in the message."""
    words = {_normalise(word) for word in re.findall(r"[\w-]+", message.lower())}
    ignored = {
        "i", "me", "my", "a", "an", "the", "want", "to", "return", "replace",
        "received", "wrong", "damaged", "item", "product", "one", "from",
        "yesterday", "today", "order", "can", "please", "help", "showing", "about"
    }
    terms = {word for word in words if word not in ignored and len(word) > 2}
    if not terms:
        return orders
    matches = []
    for order in orders:
        searchable = {
            _normalise(x) for item in order.get("items", [])
            for x in (item.get("product_name", ""), item.get("category", ""))
        }
        # Add common aliases for tech products (e.g. tv -> monitor/display)
        if any("monitor" in s or "display" in s for s in searchable):
            searchable.update({"tv", "television", "screen"})
        if any(term in token or token in term for term in terms for token in searchable):
            matches.append(order)
    return matches


def _mentioned_order_id(message: str, orders: list[dict]) -> int | None:
    # Exclude negated or complaint patterns like "showing me about order 32", "why order 32", "not order 32"
    cleaned = re.sub(r"(?:showing me|why are you showing|not|instead of)\s+(?:about\s+)?(?:order\s*#?\s*|#)\d+", "", message, flags=re.IGNORECASE)
    ids = {int(value) for value in re.findall(r"(?:order\s*#?\s*|#)(\d+)", cleaned.lower())}
    for order in orders:
        if order["id"] in ids:
            return order["id"]
    return None


def _referenced_order_id(message: str, orders: list[dict], history: list[dict]) -> int | None:
    # 1. Direct mention in the current turn
    direct = _mentioned_order_id(message, orders)
    if direct:
        return direct

    # 2. Match order by product name or keywords in current message
    current_matches = _matching_orders(message, orders)
    if len(current_matches) == 1:
        return current_matches[0]["id"]

    # 3. Contextual resolution from conversation history
    # Search backwards for product mentions or order mentions in prior conversation turns
    for turn in reversed(history):
        content = str(turn.get("content", ""))
        # Check if previous turn mentioned a specific order
        prev_order_id = _mentioned_order_id(content, orders)
        if prev_order_id:
            return prev_order_id
        # Check if previous turn mentioned a product matching one of our orders
        prev_matches = _matching_orders(content, orders)
        if len(prev_matches) == 1:
            return prev_matches[0]["id"]

    if len(orders) == 1:
        return orders[0]["id"]
    return None


def _normalise(value: str) -> str:
    value = re.sub(r"[^a-z0-9]", "", value.lower())
    return value[:-1] if value.endswith("s") else value


def _reason_from_message(message: str) -> str | None:
    match = re.search(r"(?:because|reason is|reason:)\s+(.+)", message, re.IGNORECASE)
    return match.group(1).strip() if match else None
