"""Database Seed Script for AI Customer Support Agent.

Reads synthetic e-commerce datasets from the data/ directory and populates
the PostgreSQL database (or configured SQLAlchemy database) with:
- Customers
- Products
- Orders & Order Items
- Shipments
- Returns
- Refunds
- Support Tickets
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine
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
)

# Resolve data directory path (located at project-root/data)
ROOT_DIR = current_dir.parent
DATA_DIR = ROOT_DIR / "data"

def parse_iso_datetime(dt_str: str) -> datetime:
    """Helper to convert ISO string to datetime object."""
    if not dt_str:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(dt_str)

def load_json_file(file_path: Path):
    """Safely load and parse a JSON dataset."""
    if not file_path.exists():
        raise FileNotFoundError(f"Seed data file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def seed_database(db_url: str = None):
    target_url = db_url or settings.DATABASE_URL
    print(f"Connecting to database: {target_url.split('@')[-1] if '@' in target_url else target_url}")

    connect_args = {"check_same_thread": False} if target_url.startswith("sqlite") else {}
    engine = create_engine(target_url, connect_args=connect_args)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create all tables if they do not exist
        print("Ensuring tables are created via Base.metadata.create_all...")
        Base.metadata.create_all(bind=engine)

        # 1. Clean existing records in reverse dependency order
        print("Clearing existing data...")
        session.query(SupportTicket).delete()
        session.query(Refund).delete()
        session.query(Return).delete()
        session.query(Shipment).delete()
        session.query(OrderItem).delete()
        session.query(Order).delete()
        session.query(Product).delete()
        session.query(Customer).delete()
        session.commit()

        # 2. Seed Customers
        customers_path = DATA_DIR / "customers" / "customers.json"
        customers_data = load_json_file(customers_path)
        print(f"Seeding {len(customers_data)} customers...")
        for item in customers_data:
            customer = Customer(
                id=item["id"],
                name=item["name"],
                email=item["email"],
                phone=item["phone"],
                password_hash=item["password_hash"],
                created_at=parse_iso_datetime(item.get("created_at")),
            )
            session.add(customer)
        session.flush()

        # 3. Seed Products
        products_path = DATA_DIR / "products" / "products.json"
        products_data = load_json_file(products_path)
        print(f"Seeding {len(products_data)} products...")
        for item in products_data:
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
        session.flush()

        # 4. Seed Orders & OrderItems
        orders_path = DATA_DIR / "orders" / "orders.json"
        orders_data = load_json_file(orders_path)
        print(f"Seeding {len(orders_data)} orders...")
        for o in orders_data:
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
            session.flush()

            for item in o.get("items", []):
                order_item = OrderItem(
                    id=item["id"],
                    order_id=order.id,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    price=item["price"],
                )
                session.add(order_item)
        session.flush()

        # 5. Seed Shipments
        shipments_path = DATA_DIR / "orders" / "shipments.json"
        shipments_data = load_json_file(shipments_path)
        print(f"Seeding {len(shipments_data)} shipments...")
        for s in shipments_data:
            shipment = Shipment(
                id=s["id"],
                order_id=s["order_id"],
                carrier=s["carrier"],
                tracking_number=s["tracking_number"],
                status=s["status"],
                estimated_delivery=parse_iso_datetime(s.get("estimated_delivery")),
            )
            session.add(shipment)
        session.flush()

        # 6. Seed Returns
        returns_path = DATA_DIR / "orders" / "returns.json"
        returns_data = load_json_file(returns_path)
        print(f"Seeding {len(returns_data)} returns...")
        for r in returns_data:
            ret = Return(
                id=r["id"],
                order_id=r["order_id"],
                order_item_id=r["order_item_id"],
                reason=r["reason"],
                status=r["status"],
                created_at=parse_iso_datetime(r.get("created_at")),
            )
            session.add(ret)
        session.flush()

        # 7. Seed Refunds
        refunds_path = DATA_DIR / "orders" / "refunds.json"
        refunds_data = load_json_file(refunds_path)
        print(f"Seeding {len(refunds_data)} refunds...")
        for ref in refunds_data:
            refund = Refund(
                id=ref["id"],
                order_id=ref["order_id"],
                amount=ref["amount"],
                status=ref["status"],
                created_at=parse_iso_datetime(ref.get("created_at")),
            )
            session.add(refund)
        session.flush()

        # 8. Seed Support Tickets
        tickets_path = DATA_DIR / "orders" / "tickets.json"
        tickets_data = load_json_file(tickets_path)
        print(f"Seeding {len(tickets_data)} support tickets...")
        for t in tickets_data:
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

        session.commit()

        # In PostgreSQL, synchronize primary key sequences to max(id) so dynamic inserts succeed
        if target_url.startswith("postgresql"):
            print("Synchronizing PostgreSQL primary key sequences...")
            from sqlalchemy import text
            tables = [
                "customers", "products", "orders", "order_items",
                "shipments", "returns", "refunds", "support_tickets"
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

        print("Successfully seeded all database tables!")

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
