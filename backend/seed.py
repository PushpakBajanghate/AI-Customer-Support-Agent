"""Database Seed Script for AI Customer Support Agent.

Reads synthetic e-commerce datasets from the data/ directory and safely,
additively populates the PostgreSQL database (or configured SQLAlchemy database) with:
- Customers
- Products
- Orders & Order Items
- Shipments
- Returns
- Refunds
- Support Tickets
- Conversations
- Conversation Messages

This script is completely additive, non-destructive, and idempotent.
It preserves existing records and user data.
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in python path
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from app.config import settings
from app.database import Base
from app.models import (
    Customer,
    Product,
    Order,
    OrderItem,
    Shipment,
    Return,
    Refund,
    SupportTicket,
    Conversation,
    ConversationMessage,
)

# Resolve data directory path in both local development and Render monorepos.
configured_data_dir = os.getenv("SEED_DATA_DIR")
DATA_DIR = Path(configured_data_dir) if configured_data_dir else current_dir.parent / "data"
if not DATA_DIR.exists():
    service_data_dir = current_dir / "data"
    if service_data_dir.exists():
        DATA_DIR = service_data_dir

def parse_iso_datetime(dt_str: str) -> datetime:
    """Helper to convert ISO string to datetime object."""
    if not dt_str:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(dt_str)

def load_json_file(file_path: Path):
    """Safely load and parse a JSON dataset."""
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_database_url(database_url: str) -> str:
    """Use the PostgreSQL driver installed by requirements.txt."""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return database_url

def seed_database(db_url: str = None):
    target_url = normalize_database_url(db_url or settings.DATABASE_URL)
    sanitized_url = target_url.split("@")[-1] if "@" in target_url else target_url
    print(f"Connecting to database: {sanitized_url}")

    connect_args = {"check_same_thread": False} if target_url.startswith("sqlite") else {}
    engine = create_engine(target_url, connect_args=connect_args)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create all tables if they do not exist
        print("Ensuring tables are created via Base.metadata.create_all...")
        Base.metadata.create_all(bind=engine)

        # 1. Additive Seed: Customers
        customers_path = DATA_DIR / "customers" / "customers.json"
        customers_data = load_json_file(customers_path)
        existing_cust_ids = {c.id for c in session.query(Customer.id).all()}
        existing_cust_emails = {c.email for c in session.query(Customer.email).all()}
        added_customers = 0
        for item in customers_data:
            if item["id"] in existing_cust_ids or item["email"] in existing_cust_emails:
                continue
            customer = Customer(
                id=item["id"],
                name=item["name"],
                email=item["email"],
                phone=item["phone"],
                password_hash=item["password_hash"],
                created_at=parse_iso_datetime(item.get("created_at")),
            )
            session.add(customer)
            existing_cust_ids.add(item["id"])
            existing_cust_emails.add(item["email"])
            added_customers += 1
        session.flush()
        print(f"Customers: added {added_customers} (total now: {len(existing_cust_ids)})")

        # 2. Additive Seed: Products
        products_path = DATA_DIR / "products" / "products.json"
        products_data = load_json_file(products_path)
        existing_prod_ids = {p.id for p in session.query(Product.id).all()}
        added_products = 0
        for item in products_data:
            if item["id"] in existing_prod_ids:
                continue
            product = Product(
                id=item["id"],
                name=item["name"],
                category=item["category"],
                brand=item["brand"],
                price=item["price"],
                return_window_days=item.get("return_window_days", 14),
                warranty_days=item.get("warranty_days", 365),
            )
            session.add(product)
            existing_prod_ids.add(item["id"])
            added_products += 1
        session.flush()
        print(f"Products: added {added_products} (total now: {len(existing_prod_ids)})")

        # 3. Additive Seed: Orders & OrderItems
        orders_path = DATA_DIR / "orders" / "orders.json"
        orders_data = load_json_file(orders_path)
        existing_order_ids = {o.id for o in session.query(Order.id).all()}
        existing_item_ids = {i.id for i in session.query(OrderItem.id).all()}
        added_orders = 0
        added_items = 0

        for o in orders_data:
            if o["id"] not in existing_order_ids:
                # Ensure customer exists before inserting order
                if o["customer_id"] not in existing_cust_ids:
                    continue
                order = Order(
                    id=o["id"],
                    customer_id=o["customer_id"],
                    order_date=parse_iso_datetime(o.get("order_date")),
                    status=o["status"],
                    payment_status=o["payment_status"],
                    total_amount=o["total_amount"],
                    shipping_address=o["shipping_address"],
                )
                session.add(order)
                existing_order_ids.add(o["id"])
                added_orders += 1

            for item in o.get("items", []):
                if item["id"] not in existing_item_ids:
                    if item["product_id"] not in existing_prod_ids:
                        continue
                    order_item = OrderItem(
                        id=item["id"],
                        order_id=o["id"],
                        product_id=item["product_id"],
                        quantity=item["quantity"],
                        price=item["price"],
                    )
                    session.add(order_item)
                    existing_item_ids.add(item["id"])
                    added_items += 1
        session.flush()
        print(f"Orders: added {added_orders} (total now: {len(existing_order_ids)})")
        print(f"Order Items: added {added_items} (total now: {len(existing_item_ids)})")

        # 4. Additive Seed: Shipments
        shipments_path = DATA_DIR / "orders" / "shipments.json"
        shipments_data = load_json_file(shipments_path)
        existing_shipment_ids = {s.id for s in session.query(Shipment.id).all()}
        existing_shipment_orders = {s.order_id for s in session.query(Shipment.order_id).all()}
        existing_tracking_numbers = {s.tracking_number for s in session.query(Shipment.tracking_number).all()}
        added_shipments = 0

        for s in shipments_data:
            if (
                s["id"] in existing_shipment_ids
                or s["order_id"] in existing_shipment_orders
                or s["tracking_number"] in existing_tracking_numbers
            ):
                continue
            if s["order_id"] not in existing_order_ids:
                continue
            shipment = Shipment(
                id=s["id"],
                order_id=s["order_id"],
                carrier=s["carrier"],
                tracking_number=s["tracking_number"],
                status=s["status"],
                estimated_delivery=parse_iso_datetime(s.get("estimated_delivery")),
            )
            session.add(shipment)
            existing_shipment_ids.add(s["id"])
            existing_shipment_orders.add(s["order_id"])
            existing_tracking_numbers.add(s["tracking_number"])
            added_shipments += 1
        session.flush()
        print(f"Shipments: added {added_shipments} (total now: {len(existing_shipment_ids)})")

        # 5. Additive Seed: Returns
        returns_path = DATA_DIR / "orders" / "returns.json"
        returns_data = load_json_file(returns_path)
        existing_return_ids = {r.id for r in session.query(Return.id).all()}
        existing_return_pairs = {(r.order_id, r.order_item_id) for r in session.query(Return.order_id, Return.order_item_id).all()}
        added_returns = 0

        for r in returns_data:
            pair = (r["order_id"], r["order_item_id"])
            if r["id"] in existing_return_ids or pair in existing_return_pairs:
                continue
            if r["order_id"] not in existing_order_ids or r["order_item_id"] not in existing_item_ids:
                continue
            ret = Return(
                id=r["id"],
                order_id=r["order_id"],
                order_item_id=r["order_item_id"],
                reason=r["reason"],
                status=r["status"],
                created_at=parse_iso_datetime(r.get("created_at")),
            )
            session.add(ret)
            existing_return_ids.add(r["id"])
            existing_return_pairs.add(pair)
            added_returns += 1
        session.flush()
        print(f"Returns: added {added_returns} (total now: {len(existing_return_ids)})")

        # 6. Additive Seed: Refunds
        refunds_path = DATA_DIR / "orders" / "refunds.json"
        refunds_data = load_json_file(refunds_path)
        existing_refund_ids = {ref.id for ref in session.query(Refund.id).all()}
        existing_refund_orders = {ref.order_id for ref in session.query(Refund.order_id).all()}
        added_refunds = 0

        for ref in refunds_data:
            if ref["id"] in existing_refund_ids or ref["order_id"] in existing_refund_orders:
                continue
            if ref["order_id"] not in existing_order_ids:
                continue
            refund = Refund(
                id=ref["id"],
                order_id=ref["order_id"],
                amount=ref["amount"],
                status=ref["status"],
                created_at=parse_iso_datetime(ref.get("created_at")),
            )
            session.add(refund)
            existing_refund_ids.add(ref["id"])
            existing_refund_orders.add(ref["order_id"])
            added_refunds += 1
        session.flush()
        print(f"Refunds: added {added_refunds} (total now: {len(existing_refund_ids)})")

        # 7. Additive Seed: Support Tickets
        tickets_path = DATA_DIR / "orders" / "tickets.json"
        tickets_data = load_json_file(tickets_path)
        existing_ticket_ids = {t.id for t in session.query(SupportTicket.id).all()}
        added_tickets = 0

        for t in tickets_data:
            if t["id"] in existing_ticket_ids:
                continue
            if t["customer_id"] not in existing_cust_ids:
                continue
            ticket = SupportTicket(
                id=t["id"],
                customer_id=t["customer_id"],
                subject=t["subject"],
                description=t["description"],
                status=t["status"],
                priority=t["priority"],
                created_at=parse_iso_datetime(t.get("created_at")),
            )
            session.add(ticket)
            existing_ticket_ids.add(t["id"])
            added_tickets += 1
        session.flush()
        print(f"Support Tickets: added {added_tickets} (total now: {len(existing_ticket_ids)})")

        # 8. Additive Seed: Conversations
        convs_path = DATA_DIR / "orders" / "conversations.json"
        convs_data = load_json_file(convs_path)
        existing_conv_ids = {c.id for c in session.query(Conversation.id).all()}
        added_convs = 0

        for c in convs_data:
            if c["id"] in existing_conv_ids:
                continue
            if c["customer_id"] not in existing_cust_ids:
                continue
            conv = Conversation(
                id=c["id"],
                customer_id=c["customer_id"],
                created_at=parse_iso_datetime(c.get("created_at")),
                updated_at=parse_iso_datetime(c.get("updated_at")),
            )
            session.add(conv)
            existing_conv_ids.add(c["id"])
            added_convs += 1
        session.flush()
        print(f"Conversations: added {added_convs} (total now: {len(existing_conv_ids)})")

        # 9. Additive Seed: Conversation Messages
        msgs_path = DATA_DIR / "orders" / "conversation_messages.json"
        msgs_data = load_json_file(msgs_path)
        existing_msg_ids = {m.id for m in session.query(ConversationMessage.id).all()}
        added_msgs = 0

        for m in msgs_data:
            if m["id"] in existing_msg_ids:
                continue
            if m["conversation_id"] not in existing_conv_ids:
                continue
            msg = ConversationMessage(
                id=m["id"],
                conversation_id=m["conversation_id"],
                role=m["role"],
                content=m["content"],
                timestamp=parse_iso_datetime(m.get("timestamp")),
            )
            session.add(msg)
            existing_msg_ids.add(m["id"])
            added_msgs += 1
        session.flush()
        print(f"Conversation Messages: added {added_msgs} (total now: {len(existing_msg_ids)})")

        session.commit()

        # In PostgreSQL, synchronize primary key sequences to max(id) so dynamic inserts succeed
        if target_url.startswith("postgresql"):
            print("Synchronizing PostgreSQL primary key sequences...")
            tables = [
                "customers", "products", "orders", "order_items",
                "shipments", "returns", "refunds", "support_tickets",
                "conversation_messages"
            ]
            for table in tables:
                try:
                    session.execute(text(f"""
                        SELECT setval(
                            pg_get_serial_sequence('{table}', 'id'),
                            COALESCE((SELECT MAX(id) FROM {table}), 1),
                            (SELECT MAX(id) IS NOT NULL FROM {table})
                        );
                    """))
                except Exception as seq_err:
                    print(f"Notice: sequence for {table} not updated: {seq_err}")
            session.commit()

        print("Successfully completed safe additive database seeding!")

    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {e}", file=sys.stderr)
        raise
    finally:
        session.close()

if __name__ == "__main__":
    db_arg = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "--sqlite":
            db_arg = "sqlite:///./test_dev.db"
        else:
            db_arg = sys.argv[1]
    seed_database(db_arg)
