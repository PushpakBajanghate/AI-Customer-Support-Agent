"""Production boot hook: run the additive, idempotent seed on every deploy."""

from pathlib import Path

from alembic.config import Config
from alembic import command

from app.database import Base, SessionLocal, engine
from app.models.customer import Customer
from seed import seed_database
from app.services.conversation import ensure_customer_demo_orders


def main() -> None:
    # The boot hook runs before Uvicorn's lifespan, so migrations must happen
    # here before the first database query on a fresh Render database.
    try:
        alembic_cfg = Config(str(Path(__file__).resolve().parent / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(Path(__file__).resolve().parent / "alembic"))
        command.upgrade(alembic_cfg, "head")
    except Exception:
        Base.metadata.create_all(bind=engine)

    # The seed is additive and idempotent. Running it on every deploy is what
    # makes new JSON-backed orders reach an already-populated production DB.
    seed_database()

    # Keep existing production databases additive: every profile gets the same
    # two linked demo orders on the next deploy, without replacing real data.
    session = SessionLocal()
    try:
        for customer_id, in session.query(Customer.id).all():
            ensure_customer_demo_orders(session, customer_id)
    finally:
        session.close()


if __name__ == "__main__":
    main()
