"""Chat API endpoint — Phase 5: LangGraph Router Agent.

POST /chat now routes through the full LangGraph state machine:
  1. FastAPI authenticates customer via JWT (customer_id extracted from token)
  2. AgentState initialized with runtime customer context + message
  3. LangGraph Router node classifies intent via Google Gemini
  4. LangGraph Conversational node generates the response
  5. Full response (including Router classification) returned to client

No responses, intents, routing logic, or customer data are hardcoded.
Everything is determined dynamically at runtime.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, RouterInfo
from app.schemas.router import IntentType
from app.services.auth import get_current_customer
from app.database import get_db
from app.agents.graph import run_support_graph
from app.services.conversation import (
    get_or_create_conversation,
    load_conversation_history,
    load_customer_context,
    save_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatMessageResponse,
    summary="Send a message to the AI customer support agent",
    description=(
        "Authenticates the customer via JWT Bearer token, routes their message "
        "through the LangGraph Router Agent for intent classification, and returns "
        "a dynamically generated response alongside the Router's classification."
    ),
)
def send_chat_message(
    payload: ChatMessageRequest,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """
    Processes a customer's runtime chat message through the LangGraph pipeline.

    Flow:
    1. FastAPI dependency extracts and validates JWT → customer_id
    2. LangGraph graph initialized with runtime customer context
    3. Router node classifies intent via Google Gemini (never hardcoded)
    4. Conversational node generates intent-aware response (never hardcoded)
    5. Response returned with full Router classification metadata
    """
    logger.info(
        "Chat request from customer_id=%d (%s), message_preview='%s'",
        current_customer.id,
        current_customer.name,
        payload.message[:80],
    )

    conversation = get_or_create_conversation(db, current_customer.id, payload.conversation_id)
    conversation_history = load_conversation_history(db, conversation.id)
    if not conversation_history and payload.conversation_history:
        conversation_history = payload.conversation_history
    customer_context = load_customer_context(db, current_customer.id)
    save_message(db, conversation.id, "user", payload.message)

    # Run the full LangGraph support graph with bounded persisted context.
    final_state = run_support_graph(
        customer_id=current_customer.id,
        conversation_id=conversation.id,
        customer_name=current_customer.name,
        customer_email=current_customer.email,
        message=payload.message,
        conversation_history=conversation_history,
        db_session=db,
        customer_context=customer_context,
    )

    # Extract the final response — always dynamically generated
    final_response = final_state.get("final_response") or final_state.get("router_response")

    if not final_response:
        # This should only happen if both LLM nodes completely failed
        logger.error(
            "Support graph returned no response for customer_id=%d. State error: %s",
            current_customer.id,
            final_state.get("error"),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"AI support service failed to generate a response. "
                f"Error: {final_state.get('error', 'Unknown error')}"
            ),
        )

    save_message(db, conversation.id, "assistant", final_response)
    db.commit()

    # Build the RouterInfo from graph state
    intent_str = final_state.get("intent") or "UNKNOWN"
    try:
        intent = IntentType(intent_str)
    except ValueError:
        intent = IntentType.UNKNOWN

    router_info = RouterInfo(
        intent=intent,
        confidence=final_state.get("confidence") or 0.0,
        needs_clarification=final_state.get("needs_clarification") or False,
        required_information=final_state.get("required_information") or [],
    )

    logger.info(
        "Chat response ready: customer_id=%d, intent=%s, confidence=%.2f",
        current_customer.id,
        router_info.intent,
        router_info.confidence,
    )

    return ChatMessageResponse(
        response=final_response,
        conversation_id=conversation.id,
        customer_id=current_customer.id,
        customer_name=current_customer.name,
        timestamp=datetime.now(timezone.utc),
        router=router_info,
    )
