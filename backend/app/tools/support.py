"""Small backend tools for customer-support workflows.

The LLM never receives a database session. These ordinary Python functions are
called by backend orchestration, validate ownership and business rules, and
return structured data. Write tools commit only after validation succeeds.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.refund import Refund
from app.models.return_model import Return
from app.models.shipment import Shipment
from app.models.ticket import SupportTicket
from app.models.conversation import Conversation


def get_customer_orders(customer_id: int, db: Session | None = None) -> dict[str, Any]:
    def query(session: Session) -> dict[str, Any]:
        orders = (
            session.query(Order)
            .options(joinedload(Order.order_items).joinedload(OrderItem.product))
            .filter(Order.customer_id == customer_id)
            .order_by(Order.order_date.desc())
            .all()
        )
        return {"ok": True, "data": [_order_data(order) for order in orders]}
    return _read(db, query)


def get_order(order_id: int, customer_id: int, db: Session | None = None) -> dict[str, Any]:
    def query(session: Session) -> dict[str, Any]:
        order = _owned_order(session, order_id, customer_id)
        if not order:
            return _failure("ORDER_NOT_FOUND")
        return {"ok": True, "data": _order_data(order)}
    return _read(db, query)


def track_order(order_id: int, customer_id: int, db: Session | None = None) -> dict[str, Any]:
    def query(session: Session) -> dict[str, Any]:
        order = _owned_order(session, order_id, customer_id)
        if not order:
            return _failure("ORDER_NOT_FOUND")
        shipment = session.query(Shipment).filter(Shipment.order_id == order.id).first()
        return {"ok": True, "data": {"order_id": order.id, "status": order.status, "shipment": _shipment_data(shipment)}}
    return _read(db, query)


def get_product(product_id: int, db: Session | None = None) -> dict[str, Any]:
    def query(session: Session) -> dict[str, Any]:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            return _failure("PRODUCT_NOT_FOUND")
        return {"ok": True, "data": {"id": product.id, "name": product.name, "category": product.category,
                                      "brand": product.brand, "price": product.price,
                                      "return_window_days": product.return_window_days,
                                      "warranty_days": product.warranty_days}}
    return _read(db, query)


def check_return_eligibility(order_id: int, order_item_id: int, customer_id: int, db: Session | None = None) -> dict[str, Any]:
    def query(session: Session) -> dict[str, Any]:
        item = _owned_item(session, order_id, order_item_id, customer_id)
        if not item:
            return _failure("ORDER_ITEM_NOT_FOUND")
        order = item.order
        product = item.product
        existing = session.query(Return).filter(Return.order_id == order_id, Return.order_item_id == order_item_id).first()
        days_since_order = (_utc_now() - _as_utc(order.order_date)).days
        eligible = (
            order.status == "delivered"
            and product.return_window_days > 0
            and days_since_order <= product.return_window_days
            and existing is None
        )
        reason = "ELIGIBLE" if eligible else (
            "RETURN_ALREADY_EXISTS" if existing else
            "ORDER_NOT_DELIVERED" if order.status != "delivered" else
            "RETURN_WINDOW_EXPIRED" if days_since_order > product.return_window_days else
            "PRODUCT_NOT_RETURNABLE"
        )
        return {"ok": True, "data": {"eligible": eligible, "reason": reason, "order_id": order_id,
                                      "order_item_id": order_item_id, "days_since_order": days_since_order,
                                      "return_window_days": product.return_window_days}}
    return _read(db, query)


def get_refund_status(order_id: int, customer_id: int, db: Session | None = None) -> dict[str, Any]:
    def query(session: Session) -> dict[str, Any]:
        order = _owned_order(session, order_id, customer_id)
        if not order:
            return _failure("ORDER_NOT_FOUND")
        refunds = session.query(Refund).filter(Refund.order_id == order.id).order_by(Refund.created_at.desc()).all()
        return {"ok": True, "data": {"order_id": order.id, "refunds": [_refund_data(refund) for refund in refunds]}}
    return _read(db, query)


def cancel_order(order_id: int, customer_id: int, db: Session | None = None) -> dict[str, Any]:
    def command(session: Session) -> dict[str, Any]:
        order = _owned_order(session, order_id, customer_id)
        if not order:
            return _failure("ORDER_NOT_FOUND")
        if order.status != "processing":
            return _failure("ORDER_NOT_CANCELLABLE", {"status": order.status})
        order.status = "cancelled"
        session.commit()
        return {"ok": True, "data": _order_data(order)}
    return _write(db, command)


def create_return(order_id: int, order_item_id: int, reason: str, customer_id: int, db: Session | None = None) -> dict[str, Any]:
    def command(session: Session) -> dict[str, Any]:
        if not reason or not reason.strip():
            return _failure("RETURN_REASON_REQUIRED")
        eligibility = check_return_eligibility(order_id, order_item_id, customer_id, db=session)
        if not eligibility["ok"] or not eligibility["data"]["eligible"]:
            return _failure(eligibility.get("data", {}).get("reason", "RETURN_NOT_ELIGIBLE"), eligibility.get("data"))
        new_return = Return(order_id=order_id, order_item_id=order_item_id, reason=reason.strip(), status="requested")
        session.add(new_return)
        session.commit()
        return {"ok": True, "data": {"id": new_return.id, "order_id": order_id, "order_item_id": order_item_id,
                                      "reason": new_return.reason, "status": new_return.status}}
    return _write(db, command)


def create_refund(order_id: int, customer_id: int, db: Session | None = None) -> dict[str, Any]:
    def command(session: Session) -> dict[str, Any]:
        order = _owned_order(session, order_id, customer_id)
        if not order:
            return _failure("ORDER_NOT_FOUND")
        existing = session.query(Refund).filter(Refund.order_id == order_id).first()
        if existing:
            return _failure("REFUND_ALREADY_EXISTS", _refund_data(existing))
        completed_return = session.query(Return).filter(Return.order_id == order_id, Return.status == "completed").first()
        if order.status != "cancelled" and not completed_return:
            return _failure("ORDER_NOT_REFUNDABLE", {"status": order.status})
        refund = Refund(order_id=order_id, amount=order.total_amount, status="pending")
        session.add(refund)
        order.payment_status = "pending"
        session.commit()
        return {"ok": True, "data": _refund_data(refund)}
    return _write(db, command)


def create_support_ticket(customer_id: int, subject: str, description: str, db: Session | None = None,
                          conversation_id: str | None = None, issue: str | None = None,
                          summary: str | None = None, priority: str = "medium") -> dict[str, Any]:
    def command(session: Session) -> dict[str, Any]:
        customer = session.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return _failure("CUSTOMER_NOT_FOUND")
        if not subject or not subject.strip() or not description or not description.strip():
            return _failure("TICKET_CONTENT_REQUIRED")
        if conversation_id:
            conversation = (session.query(Conversation)
                            .filter(Conversation.id == conversation_id, Conversation.customer_id == customer_id)
                            .first())
            if not conversation:
                return _failure("CONVERSATION_NOT_FOUND")
        if priority not in {"low", "medium", "high", "urgent"}:
            return _failure("INVALID_PRIORITY")
        ticket = SupportTicket(customer_id=customer_id, subject=subject.strip(), description=description.strip(),
                               conversation_id=conversation_id, issue=(issue or subject).strip(),
                               summary=(summary or description).strip(), status="open", priority=priority)
        session.add(ticket)
        session.commit()
        return {"ok": True, "data": {"id": ticket.id, "customer_id": customer_id,
                                      "conversation_id": ticket.conversation_id, "issue": ticket.issue,
                                      "summary": ticket.summary, "subject": ticket.subject,
                                      "description": ticket.description, "status": ticket.status, "priority": ticket.priority}}
    return _write(db, command)


def _read(db: Session | None, operation):
    if db is not None:
        return operation(db)
    session = SessionLocal()
    try:
        return operation(session)
    finally:
        session.close()


def _write(db: Session | None, operation):
    own_session = db is None
    session = db or SessionLocal()
    try:
        result = operation(session)
        if not result.get("ok"):
            session.rollback()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()


def _owned_order(session: Session, order_id: int, customer_id: int) -> Order | None:
    return session.query(Order).filter(Order.id == order_id, Order.customer_id == customer_id).first()


def _owned_item(session: Session, order_id: int, order_item_id: int, customer_id: int) -> OrderItem | None:
    return (session.query(OrderItem).join(Order).options(joinedload(OrderItem.product), joinedload(OrderItem.order))
            .filter(OrderItem.id == order_item_id, OrderItem.order_id == order_id, Order.customer_id == customer_id).first())


def _order_data(order: Order) -> dict[str, Any]:
    return {"id": order.id, "customer_id": order.customer_id, "order_date": _iso(order.order_date),
            "status": order.status, "payment_status": order.payment_status, "total_amount": order.total_amount,
            "shipping_address": order.shipping_address,
            "items": [{"id": item.id, "product_id": item.product_id, "product_name": item.product.name,
                       "quantity": item.quantity, "price": item.price} for item in order.order_items]}


def _shipment_data(shipment: Shipment | None) -> dict[str, Any] | None:
    if not shipment:
        return None
    return {"id": shipment.id, "order_id": shipment.order_id, "carrier": shipment.carrier,
            "tracking_number": shipment.tracking_number, "status": shipment.status,
            "estimated_delivery": _iso(shipment.estimated_delivery)}


def _refund_data(refund: Refund) -> dict[str, Any]:
    return {"id": refund.id, "order_id": refund.order_id, "amount": refund.amount,
            "status": refund.status, "created_at": _iso(refund.created_at)}


def _failure(code: str, data: Any = None) -> dict[str, Any]:
    result = {"ok": False, "error": code}
    if data is not None:
        result["data"] = data
    return result


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
