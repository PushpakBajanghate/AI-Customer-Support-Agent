"""Evaluation test fixtures providing an isolated, deterministic database state.

Creates in-memory SQLite database populated with controlled synthetic commerce data
for multi-scenario testing (customers, orders, shipments, returns, refunds, tickets).
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.shipment import Shipment
from app.models.return_model import Return
from app.models.refund import Refund
from app.models.ticket import SupportTicket
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage


def create_evaluation_db_session():
    """Builds a fresh in-memory SQLite session with full synthetic customer data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

    now = datetime.now(timezone.utc)

    # 1. Seed Products
    products = [
        Product(
            id=1,
            name="Apex Runner Shoes",
            category="Footwear",
            brand="AeroSport",
            price=120.00,
            return_window_days=30,
            warranty_days=180,
        ),
        Product(
            id=2,
            name="Arctic Windbreaker Jacket",
            category="Apparel",
            brand="NorthRidge",
            price=85.00,
            return_window_days=14,
            warranty_days=90,
        ),
        Product(
            id=3,
            name="SoundWave Pro Headphones",
            category="Electronics",
            brand="AudioZen",
            price=250.00,
            return_window_days=30,
            warranty_days=365,
        ),
        Product(
            id=4,
            name="Classic Leather Belt",
            category="Accessories",
            brand="CraftHide",
            price=45.00,
            return_window_days=30,
            warranty_days=60,
        ),
        Product(
            id=5,
            name="AeroFit Running Shorts",
            category="Apparel",
            brand="AeroSport",
            price=35.00,
            return_window_days=30,
            warranty_days=60,
        ),
        Product(
            id=6,
            name="Titan Chrono Smart Watch",
            category="Electronics",
            brand="Chronos",
            price=320.00,
            return_window_days=15,
            warranty_days=365,
        ),
        Product(
            id=7,
            name="TrailMaster Hiking Boots",
            category="Footwear",
            brand="NorthRidge",
            price=160.00,
            return_window_days=30,
            warranty_days=180,
        ),
    ]
    session.add_all(products)
    session.flush()

    # 2. Seed Customers
    # Customer 1: Alice Smith (Primary test subject)
    alice = Customer(
        id=1,
        name="Alice Smith",
        email="alice@example.com",
        phone="+1-555-0101",
        password_hash="$2b$12$fakehashforaliceinmemoryeval12345",
        created_at=now - timedelta(days=90),
    )
    # Customer 2: Bob Jones (Secondary account - isolation testing)
    bob = Customer(
        id=2,
        name="Bob Jones",
        email="bob@example.com",
        phone="+1-555-0102",
        password_hash="$2b$12$fakehashforbobinmemoryeval12345",
        created_at=now - timedelta(days=60),
    )
    # Customer 3: Carol Danvers (Refund & return history account)
    carol = Customer(
        id=3,
        name="Carol Danvers",
        email="carol@example.com",
        phone="+1-555-0103",
        password_hash="$2b$12$fakehashforcarolinmemoryeval12345",
        created_at=now - timedelta(days=45),
    )
    session.add_all([alice, bob, carol])
    session.flush()

    # 3. Seed Orders & Order Items
    # Order 101: Alice - Delivered 5 days ago (Returnable Shoes)
    order_101 = Order(
        id=101,
        customer_id=alice.id,
        order_date=now - timedelta(days=5),
        status="delivered",
        payment_status="paid",
        total_amount=120.00,
        shipping_address="123 Oak St, Springfield, IL",
    )
    # Order 102: Alice - Processing (Cancellable Jacket)
    order_102 = Order(
        id=102,
        customer_id=alice.id,
        order_date=now - timedelta(hours=12),
        status="processing",
        payment_status="paid",
        total_amount=85.00,
        shipping_address="123 Oak St, Springfield, IL",
    )
    # Order 103: Alice - Delivered 65 days ago (Expired Return Window)
    order_103 = Order(
        id=103,
        customer_id=alice.id,
        order_date=now - timedelta(days=65),
        status="delivered",
        payment_status="paid",
        total_amount=250.00,
        shipping_address="123 Oak St, Springfield, IL",
    )
    # Order 104: Alice - Shipped (Tracking & Delivery Delay Test)
    order_104 = Order(
        id=104,
        customer_id=alice.id,
        order_date=now - timedelta(days=4),
        status="shipped",
        payment_status="paid",
        total_amount=45.00,
        shipping_address="123 Oak St, Springfield, IL",
    )
    # Order 105: Alice - Cancelled, refund pending
    order_105 = Order(
        id=105,
        customer_id=alice.id,
        order_date=now - timedelta(days=10),
        status="cancelled",
        payment_status="pending",
        total_amount=35.00,
        shipping_address="123 Oak St, Springfield, IL",
    )
    # Order 201: Bob - Delivered Smart Watch (belongs to Bob, NOT Alice)
    order_201 = Order(
        id=201,
        customer_id=bob.id,
        order_date=now - timedelta(days=3),
        status="delivered",
        payment_status="paid",
        total_amount=320.00,
        shipping_address="456 Elm St, Metropolis, NY",
    )
    # Order 301: Carol - Cancelled with completed return & active refund
    order_301 = Order(
        id=301,
        customer_id=carol.id,
        order_date=now - timedelta(days=8),
        status="cancelled",
        payment_status="refunded",
        total_amount=160.00,
        shipping_address="789 Pine St, Gotham, NJ",
    )
    session.add_all([order_101, order_102, order_103, order_104, order_105, order_201, order_301])
    session.flush()

    # 4. Seed Order Items
    items = [
        OrderItem(id=1, order_id=101, product_id=1, quantity=1, price=120.00),
        OrderItem(id=2, order_id=102, product_id=2, quantity=1, price=85.00),
        OrderItem(id=3, order_id=103, product_id=3, quantity=1, price=250.00),
        OrderItem(id=4, order_id=104, product_id=4, quantity=1, price=45.00),
        OrderItem(id=5, order_id=105, product_id=5, quantity=1, price=35.00),
        OrderItem(id=6, order_id=201, product_id=6, quantity=1, price=320.00),
        OrderItem(id=7, order_id=301, product_id=7, quantity=1, price=160.00),
    ]
    session.add_all(items)
    session.flush()

    # 5. Seed Shipments
    shipments = [
        Shipment(
            id=1,
            order_id=101,
            carrier="FedEx",
            tracking_number="FDX-101-DELIVERED",
            status="delivered",
            estimated_delivery=now - timedelta(days=5),
        ),
        Shipment(
            id=2,
            order_id=104,
            carrier="DHL Express",
            tracking_number="DHL-104-TRANSIT",
            status="in_transit",
            estimated_delivery=now + timedelta(days=1),
        ),
        Shipment(
            id=3,
            order_id=201,
            carrier="UPS",
            tracking_number="UPS-201-BOB",
            status="delivered",
            estimated_delivery=now - timedelta(days=3),
        ),
    ]
    session.add_all(shipments)
    session.flush()

    # 6. Seed Returns
    returns = [
        Return(
            id=1,
            order_id=301,
            order_item_id=7,
            reason="Size too large",
            status="completed",
            created_at=now - timedelta(days=7),
        ),
    ]
    session.add_all(returns)
    session.flush()

    # 7. Seed Refunds
    refunds = [
        Refund(
            id=1,
            order_id=301,
            amount=160.00,
            status="completed",
            created_at=now - timedelta(days=6),
        ),
    ]
    session.add_all(refunds)
    session.flush()

    # 8. Seed Default Conversation
    conv = Conversation(
        id="eval-conv-alice-01",
        customer_id=alice.id,
        created_at=now - timedelta(hours=1),
        updated_at=now,
    )
    session.add(conv)
    session.commit()

    return session
