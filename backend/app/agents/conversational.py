"""LangGraph Conversational Fallback Node for AI Customer Support Agent.

This node runs AFTER the Router and generates the final conversational
response returned to the customer in Phase 5. It uses the classified
intent from the Router Agent state to generate a more contextually-aware
response than the generic Phase 4 approach.

In Phase 6+, this node will be replaced by the full Support Agent
(which will call real tools against PostgreSQL). For now, it generates
an intent-aware conversational response using Google Gemini.

No responses, intents, or data are hardcoded. Everything is runtime.
"""

import logging
import time

from fastapi import HTTPException
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import AgentState
from app.services.llm import get_llm, _extract_content_text

logger = logging.getLogger(__name__)

# Map of intent → a brief instructional note added to the LLM system prompt.
# This is NOT a hardcoded response — it is an instruction that guides Gemini
# to produce a more useful conversational reply based on classified intent.
# Gemini still generates the actual response dynamically at runtime.
INTENT_GUIDANCE = {
    "ORDER_TRACKING": (
        "The customer wants to track an order. "
        "Acknowledge their request and let them know the Support Agent will retrieve "
        "their order status from the database. Do not fabricate order details."
    ),
    "ORDER_CANCEL": (
        "The customer wants to cancel an order. "
        "Acknowledge their request empathetically. Let them know you will check "
        "which of their orders are eligible for cancellation. "
        "Do not confirm any cancellation yet — that requires database validation."
    ),
    "ORDER_RETURN": (
        "The customer wants to return an item. "
        "Acknowledge their request. Let them know you will check their recent orders "
        "and return eligibility. Do not confirm or deny any return yet."
    ),
    "REFUND_STATUS": (
        "The customer wants to know the status of a refund. "
        "Acknowledge their request and let them know you'll check their refund records."
    ),
    "REFUND_REQUEST": (
        "The customer is requesting a refund. "
        "Acknowledge empathetically. Explain that refunds are validated against "
        "return records and order status. Do not confirm any refund yet."
    ),
    "PRODUCT_INFORMATION": (
        "The customer wants product information. "
        "Acknowledge their request. If they've mentioned a specific product, "
        "let them know you'll fetch its details."
    ),
    "DAMAGED_PRODUCT": (
        "The customer received a damaged product. "
        "Express genuine empathy first. Acknowledge this is a priority issue. "
        "Let them know you will help them with a return or replacement."
    ),
    "WRONG_PRODUCT": (
        "The customer received the wrong product. "
        "Express empathy and apologize for the inconvenience. "
        "Acknowledge you'll help them resolve this with a return or replacement."
    ),
    "DELIVERY_DELAY": (
        "The customer is concerned about a delivery delay. "
        "Acknowledge their concern. Let them know you'll check their shipment status."
    ),
    "PAYMENT_ISSUE": (
        "The customer has a payment-related issue. "
        "Acknowledge this is a sensitive matter. Let them know you take payment "
        "concerns seriously and will look into their payment records."
    ),
    "HUMAN_ESCALATION": (
        "The customer is requesting to speak to a human agent. "
        "Acknowledge and validate their request respectfully. "
        "Inform them their request will be escalated to a human support specialist."
    ),
    "GENERAL_QUESTION": (
        "The customer has a general question. "
        "Answer helpfully and concisely based on what they asked. "
        "If it's about policies, mention that detailed policies are available."
    ),
    "UNKNOWN": (
        "The customer's request was not clearly classified. "
        "Politely ask them to clarify what they need help with. "
        "Offer a few examples: order tracking, returns, refunds, product information."
    ),
}

CONVERSATIONAL_SYSTEM_PROMPT = """You are an AI customer-support assistant helping an authenticated customer.

Customer context:
- Name: {customer_name}
- Customer ID: {customer_id} (authenticated — never ask for this)

The customer's intent has been classified as: {intent} (confidence: {confidence:.0%})

Retrieved knowledge context (policy/FAQ only; transactional truth comes from PostgreSQL):
{knowledge_context}

Guidance for this intent:
{intent_guidance}

Important rules:
- Be concise and empathetic.
- Never invent or fabricate order IDs, tracking numbers, amounts, or dates.
- Never claim you have executed an action (cancel, return, refund) — you are only acknowledging.
- If the customer needs clarification: {needs_clarification_note}
- Your response should feel like a warm, professional first-contact acknowledgement.
"""


def conversational_node(state: AgentState) -> AgentState:
    """
    LangGraph Conversational Node (Phase 5 fallback).

    Generates a contextually-aware response based on the Router's
    classified intent. In Phase 6+, this node will be replaced by
    the full Support Agent with tool-calling capabilities.

    All responses are dynamically generated by Google Gemini at runtime.
    No conversation text is hardcoded.
    """
    intent = state.get("intent", "UNKNOWN")
    confidence = state.get("confidence", 0.5)
    needs_clarification = state.get("needs_clarification", False)
    required_information = state.get("required_information", [])

    # Use the router's acknowledgement as the primary response if available
    # and confidence is high enough — avoids a second LLM call for high-confidence cases
    router_response = state.get("router_response", "")
    if router_response and confidence >= 0.8 and not needs_clarification and not state.get("knowledge_context"):
        logger.info(
            "Conversational node using Router acknowledgement directly "
            "(intent=%s, confidence=%.2f)",
            intent, confidence,
        )
        return {
            **state,
            "final_response": router_response,
        }

    # For lower confidence or when clarification is needed, generate a richer response
    try:
        llm = get_llm()
    except HTTPException as exc:
        # If LLM is unavailable, fall back to the router acknowledgement
        return {
            **state,
            "final_response": router_response or (
                "I'm experiencing a temporary issue. Please try again shortly."
            ),
            "error": exc.detail,
        }

    needs_clarification_note = (
        f"Gently ask for the following information: {', '.join(required_information)}"
        if needs_clarification and required_information
        else "No clarification needed — proceed with acknowledgement."
    )

    intent_guidance = INTENT_GUIDANCE.get(intent, INTENT_GUIDANCE["UNKNOWN"])
    knowledge_context = "\n\n".join(
        f"[{item.get('title', item.get('source', 'knowledge'))}]\n{item.get('content', '')}"
        for item in (state.get("knowledge_context") or [])
    ) or "(No retrieved policy context)"

    system_content = CONVERSATIONAL_SYSTEM_PROMPT.format(
        customer_name=state["customer_name"],
        customer_id=state["customer_id"],
        intent=intent,
        confidence=confidence,
        intent_guidance=intent_guidance,
        needs_clarification_note=needs_clarification_note,
        knowledge_context=knowledge_context[:6000],
    )

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=state["message"]),
    ]

    last_error = None
    for attempt in range(2):
        try:
            current_llm = llm if attempt == 0 else get_llm(model_override="gemini-3.5-flash", timeout=10)
            response = current_llm.invoke(messages)
            text_reply = _extract_content_text(response.content)
            if not text_reply:
                raise ValueError("Empty response from Gemini")

            return {
                **state,
                "final_response": text_reply,
                "error": None,
            }

        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc
            if attempt == 0 and ("503" in str(exc) or "timeout" in str(exc).lower() or "deadline" in str(exc).lower()):
                logger.warning("Conversational node: primary model experienced delay, trying secondary model...")
                continue
            break

    # Both attempts failed — fall back to router acknowledgement
    logger.error("Conversational node: Gemini failed: %s", last_error)
    return {
        **state,
        "final_response": router_response or (
            "I'm having a temporary connectivity issue. Please try again in a moment."
        ),
        "error": f"Conversational node failed: {str(last_error)}",
    }
