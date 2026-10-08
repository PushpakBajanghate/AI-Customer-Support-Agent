from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

class ChatMessageRequest(BaseModel):
    """Payload for customer sending a chat message."""
    message: str = Field(..., min_length=1, max_length=2000, description="Customer message text")
    conversation_id: Optional[str] = Field(default=None, description="Optional conversation identifier")

class ChatMessageResponse(BaseModel):
    """Response returned by chat endpoint."""
    response: str
    customer_id: int
    customer_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
