"""Router Agent Node for AI Customer Support Agent.

The Router Agent is the first node in the LangGraph state machine.
Its ONLY responsibility is intent classification — understanding what
the customer needs and routing them to the correct workflow.

The Router does NOT:
- Query the database
- Perform business actions (cancel orders, create returns, etc.)
- Fabricate specific order data
- Make assumptions about the customer's account

The Router DOES:
- Classify customer intent into one of the supported IntentType values
- Return a confidence score (0.0 – 1.0) reflecting certainty
- Flag when it needs_clarification (e.g. ambiguous between two intents)
- List any required_information the downstream agent will need
- Generate a brief, natural acknowledgement response to the customer

All routing decisions are made dynamically by Google Gemini at runtime.
No intent values, responses, or routing paths are hardcoded.
"""

import json
import logging
import time
from typing import Any

from fastapi import HTTPException, status
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException

from app.agents.state import AgentState
from app.services.llm import get_llm, _extract_content_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported intents — exhaustive list, defined once here.
# The Router LLM is instructed to return exactly one of these values.
# ---------------------------------------------------------------------------
SUPPORTED_INTENTS = [
    "ORDER_TRACKING",
    "ORDER_CANCEL",
    "ORDER_RETURN",
    "REFUND_STATUS",
    "REFUND_REQUEST",
    "PRODUCT_INFORMATION",
    "DAMAGED_PRODUCT",
    "WRONG_PRODUCT",
    "DELIVERY_DELAY",
    "PAYMENT_ISSUE",
    "HUMAN_ESCALATION",
    "GENERAL_QUESTION",
    "UNKNOWN",
]

# ---------------------------------------------------------------------------
# Router System Prompt — instructs Gemini to act as a classifier only.
# The prompt is loaded dynamically with customer context at runtime.
# ---------------------------------------------------------------------------
ROUTER_SYSTEM_PROMPT = """You are the Intent Router Agent for an AI customer support system.

Your ONLY job is to analyze the customer's message and classify their intent.

You do NOT:
- Perform any business actions (cancel orders, create returns, process refunds)
- Look up specific order data or customer account details
- Make assumptions about specific order numbers unless the customer explicitly provides them
- Reveal internal system details

You MUST respond with a JSON object (and nothing else) with exactly these fields:
{{
  "intent": "<one of the SUPPORTED_INTENTS>",
  "confidence": <float between 0.0 and 1.0>,
  "needs_clarification": <true or false>,
  "required_information": [<list of missing info strings, empty if none>],
  "acknowledgement": "<brief, empathetic 1-2 sentence response to the customer>"
}}

SUPPORTED_INTENTS:
{intents}

Rules:
- intent: Choose the SINGLE best matching intent. Default to UNKNOWN if none fits.
- confidence: How certain you are (1.0 = absolutely certain, 0.5 = unsure).
- needs_clarification: true only if the message is genuinely ambiguous between multiple very different intents. Do NOT ask for info the Support Agent can find from the customer's account (e.g. order numbers).
- required_information: List ONLY information that is fundamentally missing and cannot be retrieved from the customer's order history (e.g. if they say "I need help" with no context at all).
- acknowledgement: A warm, brief response that acknowledges the customer's request without making promises or performing actions.

Customer context:
Relevant customer context (use only to understand references; do not invent beyond it):
{customer_context}
- Name: {customer_name}
- Customer ID: {customer_id} (this is authenticated — never ask the customer for their ID)

Conversation history (most recent last):
{conversation_history}

Customer's current message:
{message}

Respond ONLY with the JSON object. No other text."""


def _format_conversation_history(history: list[dict[str, Any]]) -> str:
    """Formats conversation history for injection into the Router prompt."""
    if not history:
        return "(No prior messages — this is the start of the conversation)"
    lines = []
    for turn in history[-10:]:  # Only include last 10 turns to avoid token overflow
        role = turn.get("role", "unknown").upper()
        content = turn.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _format_customer_context(context: dict[str, Any] | None) -> str:
    if not context:
        return "(No customer context loaded)"
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))[:6000]


def _parse_router_output(raw_text: str) -> dict[str, Any]:
    """
    Parses the JSON output from the Router LLM.
    Returns a validated dict with all required fields.
    Raises ValueError if parsing fails.
    """
    # Strip any markdown code fences the model might add
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Router LLM returned invalid JSON: {e}\nRaw: {raw_text[:500]}")

    # Validate intent
    intent = str(data.get("intent", "UNKNOWN")).strip().upper()
    if intent not in SUPPORTED_INTENTS:
        logger.warning("Router returned unknown intent '%s', defaulting to UNKNOWN", intent)
        intent = "UNKNOWN"

    # Validate confidence (clamp to 0.0–1.0)
    try:
        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5

    needs_clarification = bool(data.get("needs_clarification", False))

    required_information = data.get("required_information", [])
    if not isinstance(required_information, list):
        required_information = []

    acknowledgement = str(data.get("acknowledgement", "")).strip()
    if not acknowledgement:
        acknowledgement = "I understand your request. Let me help you with that."

    return {
        "intent": intent,
        "confidence": confidence,
        "needs_clarification": needs_clarification,
        "required_information": required_information,
        "acknowledgement": acknowledgement,
    }


def router_node(state: AgentState) -> AgentState:
    """
    LangGraph Router Node.

    Receives the full AgentState (with customer context and message),
    invokes Google Gemini to classify intent dynamically at runtime,
    and returns the updated state with intent classification fields populated.

    This node NEVER hardcodes intents, responses, or routing decisions.
    All classification is performed by the live Gemini API.

    Error handling:
    - HTTP 500 (configuration errors, e.g. missing API key): re-raised to propagate
    - HTTP 502/503 (transient Gemini failures): graceful UNKNOWN fallback
    """
    try:
        llm = get_llm()
    except HTTPException as exc:
        logger.error("Router: LLM initialization failed: %s", exc.detail)
        # Configuration errors (500) must propagate — they are not transient
        if exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            raise
        # Other errors (e.g. 502) can be handled gracefully
        return {
            **state,
            "intent": "UNKNOWN",
            "confidence": 0.0,
            "needs_clarification": False,
            "required_information": [],
            "router_response": "I'm having trouble connecting to my AI services right now. Please try again shortly.",
            "error": exc.detail,
        }

    # Build the Router prompt dynamically with runtime customer context
    prompt_content = ROUTER_SYSTEM_PROMPT.format(
        intents="\n".join(f"  - {i}" for i in SUPPORTED_INTENTS),
        customer_name=state["customer_name"],
        customer_id=state["customer_id"],
        customer_context=_format_customer_context(state.get("customer_context")),
        conversation_history=_format_conversation_history(
            state.get("conversation_history", [])
        ),
        message=state["message"],
    )

    messages = [
        SystemMessage(content=prompt_content),
        HumanMessage(content=state["message"]),
    ]

    last_error = None
    for attempt in range(2):
        try:
            response = llm.invoke(messages)
            raw_text = _extract_content_text(response.content)

            parsed = _parse_router_output(raw_text)

            logger.info(
                "Router classified intent='%s' confidence=%.2f for customer_id=%d",
                parsed["intent"],
                parsed["confidence"],
                state["customer_id"],
            )

            return {
                **state,
                "intent": parsed["intent"],
                "confidence": parsed["confidence"],
                "needs_clarification": parsed["needs_clarification"],
                "required_information": parsed["required_information"],
                "router_response": parsed["acknowledgement"],
                "error": None,
            }

        except (HTTPException, ValueError) as exc:
            last_error = exc
            break
        except Exception as exc:
            last_error = exc
            if "503" in str(exc) and attempt == 0:
                logger.warning("Router: Gemini 503, retrying after 1.5s...")
                time.sleep(1.5)
                continue
            break

    # If we reach here, both attempts failed
    logger.error("Router: All attempts failed: %s", last_error)
    error_msg = str(last_error) if last_error else "Unknown error"
    return {
        **state,
        "intent": "UNKNOWN",
        "confidence": 0.0,
        "needs_clarification": False,
        "required_information": [],
        "router_response": (
            "I'm experiencing a temporary issue understanding your request. "
            "Please try rephrasing your message or contact support."
        ),
        "error": f"Router node failed: {error_msg}",
    }
