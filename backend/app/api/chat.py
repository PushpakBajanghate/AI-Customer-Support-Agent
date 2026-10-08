from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.models.customer import Customer
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.auth import get_current_customer

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post(
    "",
    response_model=ChatMessageResponse,
    summary="Send a message to customer support"
)
def send_chat_message(
    payload: ChatMessageRequest,
    current_customer: Customer = Depends(get_current_customer)
):
    """
    Receives customer chat message and returns response.
    In Phase 3, this verifies authentication context and returns a placeholder response.
    In future phases, this will pass customer_id and message into the LangGraph support agent.
    """
    response_text = (
        f"Hello {current_customer.name}! I received your message: '{payload.message}'. "
        "Your AI support agent will process this request."
    )

    return ChatMessageResponse(
        response=response_text,
        customer_id=current_customer.id,
        customer_name=current_customer.name,
        timestamp=datetime.now(timezone.utc)
    )
