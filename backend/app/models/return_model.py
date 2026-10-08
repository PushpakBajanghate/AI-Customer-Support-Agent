from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, nullable=False)  # requested, approved, completed, rejected
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="returns")
    order_item = relationship("OrderItem", back_populates="returns")

    def __repr__(self):
        return f"<Return(id={self.id}, order_id={self.order_id}, status='{self.status}')>"
