"""LangGraph Agent State definition for AI Customer Support Agent.

The AgentState is the single source of truth that flows through the
LangGraph state machine. Each node reads from and writes to this state.
No business data is hardcoded here — all values are populated at runtime.
"""

from typing import Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    The complete runtime state passed between LangGraph nodes.

    Fields are populated dynamically at runtime:
    - customer_id / customer_name: extracted from JWT by FastAPI dependency
    - message: the actual text the customer typed (never hardcoded)
    - conversation_history: list of prior turns in this session
    - intent: classified by the Router Agent node
    - confidence: Router's classification confidence (0.0 – 1.0)
    - needs_clarification: whether the Router needs more info to be certain
    - required_information: list of fields the Router flagged as missing
    - router_response: natural-language acknowledgement from the Router node
    - final_response: the ultimate response returned to the customer
    - error: any runtime error captured during graph execution
    """
    customer_id: int
    conversation_id: str
    customer_name: str
    customer_email: str
    message: str
    conversation_history: list[dict[str, Any]]

    # --- Router Agent outputs (populated after Router node runs) ---
    intent: Optional[str]
    confidence: Optional[float]
    needs_clarification: Optional[bool]
    required_information: Optional[list[str]]

    # --- Response fields ---
    router_response: Optional[str]     # Router's acknowledgement to the customer
    final_response: Optional[str]      # Completed response (set by final node)
    error: Optional[str]               # Non-None when a node encounters an error
    db_session: Optional[Any]          # Optional legacy handle; tools manage scoped sessions
    support_context: Optional[dict[str, Any]]
    customer_context: Optional[dict[str, Any]]
    knowledge_context: Optional[list[dict[str, Any]]]
    rag_used: bool
    requested_action: Optional[dict[str, Any]]
    supervisor_result: Optional[dict[str, Any]]
    escalation_reason: Optional[str]
    escalation_priority: Optional[str]
    tool_failures: int
