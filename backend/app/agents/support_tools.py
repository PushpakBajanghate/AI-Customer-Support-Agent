"""Approved, read-only customer-support tools.

These functions are the only database access used by the Support Agent.  They
never mutate state and every customer-scoped query is constrained by the
authenticated customer id supplied by the API layer.
Scoped database sessions are instantiated per operation if no active session is supplied,
ensuring thread safety and preventing database sessions from leaking into LangGraph state.
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.shipment import Shipment
from app.models.return_model import Return
from app.models.refund import Refund
from app.models.ticket import SupportTicket


@contextmanager
def _get_session(db: Session | None = None):
    """Yields provided DB session or manages a scoped SessionLocal instance."""
    if db is not None:
        yield db
    else:
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()


def _resolve_session_and_customer(arg1: Any, arg2: Any, kwargs: dict) -> tuple[Session | None, int]:
    """Gracefully normalizes positional and keyword args whether db is passed first or customer_id is passed first."""
    if isinstance(arg1, int):
        return kwargs.get("db", None), arg1
    if isinstance(arg2, int):
        return arg1, arg2
    return kwargs.get("db", None), kwargs.get("customer_id", 0)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def get_customer_information(db: Session | None = None, customer_id: int | None = None, **kwargs) -> dict[str, Any] | None:
    db, customer_id = _resolve_session_and_customer(db, customer_id, kwargs)
    with _get_session(db) as session:
        customer = session.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return None
        return {"id": customer.id, "name": customer.name, "email": customer.email, "phone": customer.phone}


def get_recent_orders(db: Session | None = None, customer_id: int | None = None, limit: int = 10, **kwargs) -> list[dict[str, Any]]:
    db, customer_id = _resolve_session_and_customer(db, customer_id, kwargs)
    with _get_session(db) as session:
        orders = (
            session.query(Order)
            .options(joinedload(Order.order_items).joinedload(OrderItem.product))
            .filter(Order.customer_id == customer_id)
            .order_by(Order.order_date.desc())
            .limit(limit)
            .all()
        )
        return [_order_dict(order) for order in orders]


def get_order_items(db: Session | None = None, customer_id: int | None = None, order_id: int | None = None, **kwargs) -> list[dict[str, Any]]:
    db, customer_id = _resolve_session_and_customer(db, customer_id, kwargs)
    with _get_session(db) as session:
        query = (
            session.query(OrderItem)
            .join(Order)
            .options(joinedload(OrderItem.product))
            .filter(Order.customer_id == customer_id)
        )
        if order_id is not None:
            query = query.filter(OrderItem.order_id == order_id)
        return [
            {
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "category": item.product.category,
                "quantity": item.quantity,
                "price": item.price,
            }
            for item in query.all()
        ]


def get_shipments(db: Session | None = None, customer_id: int | None = None, order_id: int | None = None, **kwargs) -> list[dict[str, Any]]:
    db, customer_id = _resolve_session_and_customer(db, customer_id, kwargs)
    with _get_session(db) as session:
        query = session.query(Shipment).join(Order).filter(Order.customer_id == customer_id)
        if order_id is not None:
            query = query.filter(Shipment.order_id == order_id)
        return [
            {"id": s.id, "order_id": s.order_id, "carrier": s.carrier, "tracking_number": s.tracking_number,
             "status": s.status, "estimated_delivery": _iso(s.estimated_delivery)}
            for s in query.order_by(Shipment.id.desc()).all()
        ]


def get_returns(db: Session | None = None, customer_id: int | None = None, order_id: int | None = None, statuses: set[str] | None = None, limit: int | None = None, **kwargs) -> list[dict[str, Any]]:
    db, customer_id = _resolve_session_and_customer(db, customer_id, kwargs)
    with _get_session(db) as session:
        query = session.query(Return).join(Order).filter(Order.customer_id == customer_id)
        if order_id is not None:
            query = query.filter(Return.order_id == order_id)
        if statuses:
            query = query.filter(Return.status.in_(statuses))
        query = query.order_by(Return.id.desc())
        if limit:
            query = query.limit(limit)
        return [{"id": r.id, "order_id": r.order_id, "order_item_id": r.order_item_id, "reason": r.reason,
                 "status": r.status, "created_at": _iso(r.created_at)} for r in query.all()]


def get_refunds(db: Session | None = None, customer_id: int | None = None, order_id: int | None = None, limit: int | None = None, **kwargs) -> list[dict[str, Any]]:
    db, customer_id = _resolve_session_and_customer(db, customer_id, kwargs)
    with _get_session(db) as session:
        query = session.query(Refund).join(Order).filter(Order.customer_id == customer_id)
        if order_id is not None:
            query = query.filter(Refund.order_id == order_id)
        query = query.order_by(Refund.created_at.desc(), Refund.id.desc())
        if limit:
            query = query.limit(limit)
        return [{"id": r.id, "order_id": r.order_id, "amount": r.amount, "status": r.status,
                 "created_at": _iso(r.created_at)} for r in query.all()]


def get_support_tickets(db: Session | None = None, customer_id: int | None = None, statuses: set[str] | None = None, limit: int | None = None, **kwargs) -> list[dict[str, Any]]:
    db, customer_id = _resolve_session_and_customer(db, customer_id, kwargs)
    with _get_session(db) as session:
        query = session.query(SupportTicket).filter(SupportTicket.customer_id == customer_id)
        if statuses:
            query = query.filter(SupportTicket.status.in_(statuses))
        query = query.order_by(SupportTicket.created_at.desc())
        if limit:
            query = query.limit(limit)
        tickets = query.all()
        return [{"id": t.id, "conversation_id": t.conversation_id, "issue": t.issue,
                 "summary": t.summary, "subject": t.subject, "description": t.description,
                 "status": t.status, "priority": t.priority, "created_at": _iso(t.created_at)} for t in tickets]


def _order_dict(order: Order) -> dict[str, Any]:
    return {
        "id": order.id,
        "order_date": _iso(order.order_date),
        "status": order.status,
        "payment_status": order.payment_status,
        "total_amount": order.total_amount,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "category": item.product.category,
                "quantity": item.quantity,
                "price": item.price,
                "return_window_days": getattr(item.product, "return_window_days", 14),
                "warranty_days": getattr(item.product, "warranty_days", 365),
            }
            for item in order.order_items
        ],
    }
