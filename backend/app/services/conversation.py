from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.shipment import Shipment
from app.models.product import Product
from app.agents.support_tools import (
    get_customer_information,
    get_recent_orders,
    get_shipments,
    get_returns,
    get_refunds,
    get_support_tickets,
)
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage


HISTORY_LIMIT = 12


def ensure_customer_demo_orders(db: Session, customer_id: int):
    """Ensures accounts are provisioned with realistic active and historical orders for policy reviews."""
    all_products = db.query(Product).order_by(Product.id).all()
    if not all_products:
        return

    now = datetime.now(timezone.utc)
    existing_orders = db.query(Order).filter(Order.customer_id == customer_id).all()
    existing_order_count = len(existing_orders)

    # 1. Provision active orders if account has none
    if existing_order_count == 0:
        p1 = all_products[0]
        o1 = Order(
            customer_id=customer_id,
            order_date=now - timedelta(days=6),
            status="delivered",
            payment_status="paid",
            total_amount=p1.price,
            shipping_address="Main Delivery Address, Pune, MH 411045",
        )
        db.add(o1)
        db.flush()
        db.add(OrderItem(order_id=o1.id, product_id=p1.id, quantity=1, price=p1.price))
        db.add(Shipment(
            order_id=o1.id,
            carrier="FedEx",
            tracking_number=f"FDX-{o1.id}82-DELIV",
            status="delivered",
            estimated_delivery=now - timedelta(days=2),
        ))

        if len(all_products) > 1:
            p2 = all_products[1]
            o2 = Order(
                customer_id=customer_id,
                order_date=now - timedelta(days=2),
                status="shipped",
                payment_status="paid",
                total_amount=p2.price,
                shipping_address="Main Delivery Address, Pune, MH 411045",
            )
            db.add(o2)
            db.flush()
            db.add(OrderItem(order_id=o2.id, product_id=p2.id, quantity=1, price=p2.price))
            db.add(Shipment(
                order_id=o2.id,
                carrier="DHL Express",
                tracking_number=f"DHL-{o2.id}93-TRANSIT",
                status="in_transit",
                estimated_delivery=now + timedelta(days=1),
            ))

        if len(all_products) > 6:
            p3 = all_products[6]
            o3 = Order(
                customer_id=customer_id,
                order_date=now - timedelta(hours=4),
                status="processing",
                payment_status="paid",
                total_amount=p3.price,
                shipping_address="Main Delivery Address, Pune, MH 411045",
            )
            db.add(o3)
            db.flush()
            db.add(OrderItem(order_id=o3.id, product_id=p3.id, quantity=1, price=p3.price))

    # 2. Ensure customer has an expired return order for Return Policy Review testing
    has_expired_order = any(
        o.status == "delivered" and (now - (o.order_date.replace(tzinfo=timezone.utc) if o.order_date.tzinfo is None else o.order_date)).days > 30
        for o in existing_orders
    )
    if not has_expired_order and len(all_products) > 5:
        p_expired = all_products[5]  # ApexFit Smart Fitness Tracker Band (10-day return window)
        o_exp = Order(
            customer_id=customer_id,
            order_date=now - timedelta(days=50),
            status="delivered",
            payment_status="paid",
            total_amount=p_expired.price,
            shipping_address="Main Delivery Address, Pune, MH 411045",
        )
        db.add(o_exp)
        db.flush()
        db.add(OrderItem(order_id=o_exp.id, product_id=p_expired.id, quantity=1, price=p_expired.price))
        db.add(Shipment(
            order_id=o_exp.id,
            carrier="FedEx",
            tracking_number=f"FDX-{o_exp.id}10-PAST",
            status="delivered",
            estimated_delivery=now - timedelta(days=45),
        ))

    # 3. Ensure customer has an active warranty order for Warranty Policy Review testing
    has_warranty_order = any(
        any("Monitor" in (item.product.name if item.product else "") for item in o.order_items)
        for o in existing_orders
    )
    if not has_warranty_order and len(all_products) > 2:
        p_warranty = all_products[2]  # UltraView 27-inch 4K IPS Monitor (730-day warranty)
        o_war = Order(
            customer_id=customer_id,
            order_date=now - timedelta(days=70),
            status="delivered",
            payment_status="paid",
            total_amount=p_warranty.price,
            shipping_address="Main Delivery Address, Pune, MH 411045",
        )
        db.add(o_war)
        db.flush()
        db.add(OrderItem(order_id=o_war.id, product_id=p_warranty.id, quantity=1, price=p_warranty.price))
        db.add(Shipment(
            order_id=o_war.id,
            carrier="BlueDart",
            tracking_number=f"BLU-{o_war.id}44-WARR",
            status="delivered",
            estimated_delivery=now - timedelta(days=65),
        ))

    db.commit()


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
    """Load bounded records needed for customer support and ensure active records exist."""
    ensure_customer_demo_orders(db, customer_id)
    return {
        "customer": get_customer_information(db, customer_id),
        "recent_orders": get_recent_orders(db, customer_id, limit=5),
        "shipments": get_shipments(db, customer_id),
        "open_returns": get_returns(db, customer_id, statuses={"requested", "approved"}, limit=5),
        "recent_refunds": get_refunds(db, customer_id, limit=5),
        "open_support_tickets": get_support_tickets(db, customer_id, statuses={"open", "in_progress"}, limit=5),
    }
