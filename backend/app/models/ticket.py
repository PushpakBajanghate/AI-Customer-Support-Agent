from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True, index=True)
    issue = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="open")  # open, in_progress, resolved, closed
    priority = Column(String, nullable=False, default="medium")  # low, medium, high, urgent
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="support_tickets")
    conversation = relationship("Conversation", back_populates="support_tickets")

    def __repr__(self):
        return f"<SupportTicket(id={self.id}, customer_id={self.customer_id}, subject='{self.subject}', status='{self.status}')>"
