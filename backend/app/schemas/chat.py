"""Pydantic schemas for the Chat API endpoint.

These schemas define the request and response contracts for POST /chat.
The response now includes Router Agent output (intent classification)
in addition to the conversational response.

All field values are populated at runtime — nothing is hardcoded.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.router import IntentType


class ChatMessageRequest(BaseModel):
    """Payload for a customer sending a chat message."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Customer message text (actual runtime input, never hardcoded)"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation session identifier for multi-turn context"
    )
    conversation_history: Optional[list[dict]] = Field(
        default=None,
        description="Optional prior turns in this conversation session"
    )


class RouterInfo(BaseModel):
    """
    Router Agent classification results embedded in the chat response.

    These fields are populated dynamically by the LangGraph Router node.
    The frontend can use these to display intent badges, confidence meters,
    or route to specialized UI views in future iterations.
    """
    intent: IntentType = Field(..., description="Classified customer intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    needs_clarification: bool = Field(..., description="Whether clarification was requested")
    required_information: list[str] = Field(
        default_factory=list,
        description="Missing information flagged by the Router"
    )


class ChatMessageResponse(BaseModel):
    """
    Full response returned by POST /chat.

    Includes both the conversational response and the Router classification.
    All values are dynamically generated at runtime by the LangGraph graph.
    """
    response: str = Field(..., description="AI-generated conversational response")
    customer_id: int = Field(..., description="Authenticated customer's database ID")
    customer_name: str = Field(..., description="Authenticated customer's display name")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the response was generated"
    )
    router: RouterInfo = Field(
        ...,
        description="Router Agent's intent classification results"
    )
