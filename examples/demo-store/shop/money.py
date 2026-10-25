# serves: foundation
"""Money as whole cents, so totals never pick up rounding errors."""


def cents(amount: str) -> int:
    """'12.50' -> 1250."""
    units, _, fraction = amount.partition(".")
    return int(units) * 100 + int((fraction + "00")[:2])


def shown(value: int) -> str:
    """1250 -> '12.50'."""
    return f"{value // 100}.{value % 100:02d}"
