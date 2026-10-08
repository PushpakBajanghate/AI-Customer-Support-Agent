from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    carrier = Column(String, nullable=False)
    tracking_number = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False)  # in_transit, delivered, out_for_delivery
    estimated_delivery = Column(DateTime, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="shipment")

    def __repr__(self):
        return f"<Shipment(id={self.id}, order_id={self.order_id}, tracking='{self.tracking_number}', status='{self.status}')>"
