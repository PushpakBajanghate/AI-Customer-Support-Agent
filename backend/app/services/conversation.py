"""Small PostgreSQL-backed conversation and customer-context service."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents.support_tools import (
    get_customer_information,
    get_recent_orders,
    get_returns,
    get_refunds,
    get_support_tickets,
)
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage


HISTORY_LIMIT = 12


def get_or_create_conversation(db: Session, customer_id: int, conversation_id: str | None) -> Conversation:
    if conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.customer_id == customer_id)
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return conversation

    conversation = Conversation(id=str(uuid4()), customer_id=customer_id)
    db.add(conversation)
    db.flush()
    return conversation


def load_conversation_history(db: Session, conversation_id: str) -> list[dict]:
    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.timestamp.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    return [
        {"role": message.role, "content": message.content, "timestamp": message.timestamp.isoformat()}
        for message in reversed(messages)
    ]


def save_message(db: Session, conversation_id: str, role: str, content: str) -> ConversationMessage:
    message = ConversationMessage(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = datetime.now(timezone.utc)
    db.flush()
    return message


def load_customer_context(db: Session, customer_id: int) -> dict:
    """Load only bounded records needed at the start of a chat."""
    return {
        "customer": get_customer_information(db, customer_id),
        "recent_orders": get_recent_orders(db, customer_id, limit=5),
        "open_returns": get_returns(db, customer_id, statuses={"requested", "approved"}, limit=5),
        "recent_refunds": get_refunds(db, customer_id, limit=5),
        "open_support_tickets": get_support_tickets(db, customer_id, statuses={"open", "in_progress"}, limit=5),
    }
