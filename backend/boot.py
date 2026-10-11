"""Production boot hook: seed only a brand-new database, never on redeploy."""

from pathlib import Path

from alembic.config import Config
from alembic import command

from app.database import Base, SessionLocal, engine
from app.models.customer import Customer
from seed import seed_database


def main() -> None:
    # The boot hook runs before Uvicorn's lifespan, so migrations must happen
    # here before the first database query on a fresh Render database.
    try:
        alembic_cfg = Config(str(Path(__file__).resolve().parent / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(Path(__file__).resolve().parent / "alembic"))
        command.upgrade(alembic_cfg, "head")
    except Exception:
        Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        has_customers = session.query(Customer.id).first() is not None
    finally:
        session.close()

    if not has_customers:
        seed_database()


if __name__ == "__main__":
    main()
