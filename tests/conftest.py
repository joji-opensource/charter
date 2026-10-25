# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest
from click.testing import CliRunner

from dev_charter.cli import main


class Product:
    """A product folder set up with `dev-charter init`, and a way to run commands in it."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.runner = CliRunner()

    def run(self, *args: str, ok: bool = True):
        result = self.runner.invoke(main, ["--root", str(self.root), *args])
        if ok:
            assert result.exit_code == 0, result.output
        return result

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


@pytest.fixture
def product(tmp_path: Path) -> Product:
    root = tmp_path / "shop"
    root.mkdir()
    shop = Product(root)
    shop.run("init", "--name", "Demo Store", "--area", "Orders and delivery", "--area", "Checkout",
             "--role", "customer", "--yes")
    return shop


FEATURE_F014 = """---
id: F-014
title: Track my order
area: Orders and delivery
priority: Must
release: Spring launch
state: agreed
decisions: [DEC-001]
---

**As a** customer of an online store
**I want to** see where my order is and when it will arrive
**With** the current step (packed, shipped, out for delivery), the expected delivery date, and a text message
when it is out for delivery
**Must also** load in under 2 seconds on a phone · show me only my own orders
**So that** I don't have to contact support to ask where my package is

## Done means

- **a.** Every order shows its current step and expected delivery date
- **b.** A text message is sent when the order goes out for delivery
- **c.** Opening someone else's order shows a sign-in page, never their order

## Sign-offs

- 2026-10-24 · b · Joji John · received the text on a real phone during a staging order
"""

DECISION_001 = """---
id: DEC-001
title: Delivery dates come from the carrier
date: 2026-10-20
decided_by: Joji John
features: [F-014]
---

**Decision** The expected delivery date shown to customers is the carrier's date.
**Instead of** Estimating it ourselves from past deliveries.
**Because** Customers trust the carrier's date, and ours would disagree with the carrier's own messages.
"""
