# serves: F-014, P-001
"""Where an order is and when it will arrive, shown only to the customer who placed it."""

from dataclasses import dataclass
from datetime import date

STEPS = ("packed", "shipped", "out for delivery", "delivered")


class SignInRequired(Exception):
    """The person looking is not the order's customer, so they are sent to the sign-in page."""


@dataclass(frozen=True)
class Order:
    id: str
    customer: str
    step: str
    carrier_date: date  # the carrier's own date, never an estimate of ours (DEC-001)


def order_status(order: Order, viewer: str | None) -> dict[str, str]:
    if viewer != order.customer:
        raise SignInRequired(order.id)
    if order.step not in STEPS:
        raise ValueError(f"unknown step {order.step!r}")
    return {"step": order.step, "expected": order.carrier_date.isoformat()}
