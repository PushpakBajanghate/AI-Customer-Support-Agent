"""LangGraph StateGraph definition for AI Customer Support Agent.

Phase 6: Defines and compiles the LangGraph graph.

Current graph topology (Phase 6):
  START → router_node → (support_agent_node | conversational_node) → END

In Phase 6+, conditional edges will be added to route from
router_node to specialized support tool nodes based on intent.

The graph is compiled once at module import time and reused across
all requests for efficiency. All state is initialized per-request.
"""

import logging

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.router import router_node
from app.agents.conversational import conversational_node
from app.agents.support import support_agent_node

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graph Definition
# ---------------------------------------------------------------------------

def _build_graph() -> any:
    """Builds and compiles the LangGraph StateGraph."""

    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("router", router_node)
    graph.add_node("conversational", conversational_node)
    graph.add_node("support", support_agent_node)

    # Define edges
    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        lambda state: "support" if state.get("intent") in {
            "ORDER_TRACKING", "ORDER_CANCEL", "ORDER_RETURN", "REFUND_STATUS",
            "REFUND_REQUEST", "DAMAGED_PRODUCT", "WRONG_PRODUCT", "DELIVERY_DELAY",
            "PAYMENT_ISSUE",
        } else "conversational",
        {"support": "support", "conversational": "conversational"},
    )
    graph.add_edge("support", END)
    graph.add_edge("conversational", END)

    compiled = graph.compile()
    logger.info("LangGraph state machine compiled successfully (Phase 6 topology)")
    return compiled


# Compile once at module load time — thread-safe, reused per request
support_graph = _build_graph()


def run_support_graph(
    customer_id: int,
    customer_name: str,
    customer_email: str,
    message: str,
    conversation_history: list | None = None,
    db_session=None,
    customer_context: dict | None = None,
) -> AgentState:
    """
    Initializes and runs the LangGraph support graph for a single request.

    All inputs are runtime values — nothing is hardcoded.
    Returns the final AgentState after all nodes have executed.

    Args:
        customer_id: Authenticated customer's database ID (from JWT).
        customer_name: Customer's display name (from database).
        customer_email: Customer's email address.
        message: The actual text message submitted by the customer.
        conversation_history: Optional prior turns in this session.

    Returns:
        Final AgentState with intent, confidence, and final_response populated.
    """
    initial_state: AgentState = {
        "customer_id": customer_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "message": message,
        "conversation_history": conversation_history or [],
        # --- Router outputs (initially None) ---
        "intent": None,
        "confidence": None,
        "needs_clarification": None,
        "required_information": None,
        # --- Response fields ---
        "router_response": None,
        "final_response": None,
        "error": None,
        "db_session": db_session,
        "support_context": None,
        "customer_context": customer_context,
    }

    logger.info(
        "Running support graph for customer_id=%d, message_preview='%s'",
        customer_id,
        message[:80],
    )

    final_state: AgentState = support_graph.invoke(initial_state)

    logger.info(
        "Support graph completed: intent=%s, confidence=%.2f, has_error=%s",
        final_state.get("intent"),
        final_state.get("confidence") or 0.0,
        bool(final_state.get("error")),
    )

    return final_state
