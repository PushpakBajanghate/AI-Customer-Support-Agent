from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.models.customer import Customer
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.auth import get_current_customer
from app.services.llm import generate_support_response

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
    1. Authenticates customer via JWT Bearer token
    2. Receives customer message
    3. Sends message to configured LLM (Google Gemini) with system prompt
    4. Receives model response
    5. Returns response to customer
    """
    ai_response = generate_support_response(current_customer, payload.message)

    return ChatMessageResponse(
        response=ai_response,
        customer_id=current_customer.id,
        customer_name=current_customer.name,
        timestamp=datetime.now(timezone.utc)
    )
