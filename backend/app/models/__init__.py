"""SQLAlchemy database models for AI Customer Support Agent."""
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.shipment import Shipment
from app.models.return_model import Return
from app.models.refund import Refund
from app.models.ticket import SupportTicket

__all__ = [
    "Customer",
    "Product",
    "Order",
    "OrderItem",
    "Shipment",
    "Return",
    "Refund",
    "SupportTicket",
]
