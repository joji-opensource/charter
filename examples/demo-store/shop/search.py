# serves: F-011
"""Finding products by name, forgiving small spelling mistakes."""

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class Product:
    name: str
    price: int  # cents
    in_stock: bool


def search(products: list[Product], query: str) -> list[Product]:
    query = query.lower().strip()

    def score(product: Product) -> float:
        name = product.name.lower()
        return 1.0 if name == query else SequenceMatcher(None, query, name).ratio()

    ranked = sorted(products, key=score, reverse=True)
    return [p for p in ranked if score(p) >= 0.8]
