"""add foreign key performance indexes

Revision ID: 7a82b9c3d4e5
Revises: ee345c9db243
Create Date: 2026-10-12 18:38:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a82b9c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'ee345c9db243'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with lookup performance indexes."""
    op.create_index(op.f('ix_orders_customer_id'), 'orders', ['customer_id'], unique=False)
    op.create_index(op.f('ix_order_items_order_id'), 'order_items', ['order_id'], unique=False)
    op.create_index(op.f('ix_support_tickets_customer_id'), 'support_tickets', ['customer_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_support_tickets_customer_id'), table_name='support_tickets')
    op.drop_index(op.f('ix_order_items_order_id'), table_name='order_items')
    op.drop_index(op.f('ix_orders_customer_id'), table_name='orders')
