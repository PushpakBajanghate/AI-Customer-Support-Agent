"""Pydantic schemas for Router Agent outputs.

These schemas define the structured data that flows out of the Router Agent
and back to the API consumer. All values are populated at runtime by the
LangGraph Router node — nothing is hardcoded.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Exhaustive list of customer support intents the Router can classify."""
    ORDER_TRACKING = "ORDER_TRACKING"
    ORDER_CANCEL = "ORDER_CANCEL"
    ORDER_RETURN = "ORDER_RETURN"
    REFUND_STATUS = "REFUND_STATUS"
    REFUND_REQUEST = "REFUND_REQUEST"
    PRODUCT_INFORMATION = "PRODUCT_INFORMATION"
    DAMAGED_PRODUCT = "DAMAGED_PRODUCT"
    WRONG_PRODUCT = "WRONG_PRODUCT"
    DELIVERY_DELAY = "DELIVERY_DELAY"
    PAYMENT_ISSUE = "PAYMENT_ISSUE"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    GENERAL_QUESTION = "GENERAL_QUESTION"
    UNKNOWN = "UNKNOWN"


class RouterOutput(BaseModel):
    """
    Structured output of the Router Agent's intent classification.

    All fields are populated dynamically by Google Gemini at runtime.
    No field values are hardcoded.
    """
    intent: IntentType = Field(
        ...,
        description="The classified customer intent."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classification confidence score (0.0 = no confidence, 1.0 = certain)."
    )
    needs_clarification: bool = Field(
        ...,
        description="True when the message is ambiguous and requires customer clarification."
    )
    required_information: list[str] = Field(
        default_factory=list,
        description="Information the Router flagged as missing for downstream processing."
    )
