# serves: F-013, P-002
"""Paying with a saved card. The payment provider keeps the card; we keep only its token (DEC-002)."""

from dataclasses import dataclass

from .money import shown


@dataclass(frozen=True)
class SavedCard:
    token: str  # the payment provider's reference; the card number itself never reaches us
    last_four: str

    def label(self) -> str:
        return f"Card ending {self.last_four}"


class PriceChanged(Exception):
    """The total changed after the customer saw it; they confirm again before paying."""


def confirm_screen(card: SavedCard, total: int) -> str:
    return f"Pay {shown(total)} with {card.label()}"


# serves: P-002.b — a changed price is confirmed before paying
def charge(card: SavedCard, total_shown: int, total_now: int) -> dict[str, object]:
    if total_now != total_shown:
        raise PriceChanged(f"{shown(total_shown)} became {shown(total_now)}")
    return {"token": card.token, "amount": total_now}
