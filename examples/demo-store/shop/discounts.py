"""Seasonal discounts from an earlier version of the store. No feature asks for this today."""


def seasonal_discount(total: int, season: str) -> int:
    return total * 9 // 10 if season == "winter" else total
