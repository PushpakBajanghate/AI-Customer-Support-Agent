"""Customer support tools executed by the backend on behalf of the agent."""

from app.tools.support import (
    cancel_order,
    check_return_eligibility,
    create_refund,
    create_return,
    create_support_ticket,
    get_customer_orders,
    get_order,
    get_product,
    get_refund_status,
    track_order,
)

__all__ = [
    "get_customer_orders", "get_order", "track_order", "get_product",
    "check_return_eligibility", "get_refund_status", "cancel_order",
    "create_return", "create_refund", "create_support_ticket",
]
