# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Tags that explain themselves (0.1.1): every tag counts, the coding agent is reminded while building, words can be
refreshed."""

import json

from click.testing import CliRunner
from openpyxl import load_workbook

from dev_charter.cli import main

from .conftest import FEATURE_F014, Product
from .test_edits import codex

FEATURE = FEATURE_F014.replace("decisions: [DEC-001]", "decisions: []")


def remind(product: Product, rel: str) -> str | None:
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(product.root / rel)}}
    result = CliRunner().invoke(main, ["remind"], input=json.dumps(payload))
    assert result.exit_code == 0
    return json.loads(result.output)["hookSpecificOutput"]["additionalContext"] if result.output.strip() else None


def test_claude_is_told_the_exact_tag_for_its_card(product: Product):
    product.write("charter/features/F-014-track-my-order.md", FEATURE)
    product.run("card", "new", "Order page", "--serves", "F-014.c")
    product.write("shop/orders.py", "def status(order):\n    return order\n")
    note = remind(product, "shop/orders.py")
    assert "shop/orders.py does not say which feature it serves" in note
    assert "CARD-001 (Order page), which serves F-014.c" in note
    assert "`# serves: F-014 — Track my order`" in note
    assert "`# serves: F-014.c — Opening someone else's order shows a sign-in page, never their order`" in note
    product.write("web/order.ts", "export const status = 1\n")
    assert "`// serves: F-014 — Track my order`" in remind(product, "web/order.ts")


def test_no_reminder_for_tagged_code_tests_or_files_outside_the_product(product: Product, tmp_path):
    product.write("shop/orders.py", "# serves: F-014\n")
    product.write("tests/test_orders.py", "def test_x():\n    pass\n")
    assert remind(product, "shop/orders.py") is None
    assert remind(product, "tests/test_orders.py") is None
    outside = tmp_path / "elsewhere.py"
    outside.write_text("x = 1\n")
    result = CliRunner().invoke(main, ["remind"], input=json.dumps({"tool_input": {"file_path": str(outside)}}))
    assert result.output.strip() == ""


def test_without_an_open_card_the_reminder_still_says_what_to_write(product: Product):
    product.write("shop/orders.py", "def status(order):\n    return order\n")
    note = remind(product, "shop/orders.py")
    assert "`# serves: F-nnn — <what it is>`" in note and "`# serves: foundation`" in note


def test_a_tag_naming_a_missing_check_is_a_problem(product: Product):
    product.write("charter/features/F-014-track-my-order.md", FEATURE)
    product.write("shop/orders.py", "# serves: F-014.z — something\n")
    result = product.run("check", ok=False)
    assert result.exit_code == 1 and "serves F-014.z, but F-014 has no check 'z.'" in result.output


def test_code_shows_under_each_check_and_in_the_code_map(product: Product):
    product.write("charter/features/F-014-track-my-order.md", FEATURE)
    product.write("shop/orders.py", "# serves: F-014 — Track my order\n\n\n"
                  "# serves: F-014.c — someone else's order asks to sign in\ndef status(order, viewer):\n    pass\n")
    product.run("report")
    book = load_workbook(product.root / "LEDGER.xlsx")
    done = book["Features"]["Q3"].value.splitlines()
    assert done[2].endswith("never their order — shop/orders.py:4")
    assert done[0].endswith("expected delivery date")
    serves = book["Code map"]["D3"].value.splitlines()
    assert serves == ["F-014 · Track my order (line 1)",
                      "F-014.c · Opening someone else's order shows a sign-in page, never their order (line 4)"]


def test_tags_refresh_brings_the_words_in_line_with_the_charter(product: Product):
    product.write("charter/features/F-014-track-my-order.md", FEATURE)
    product.write("shop/orders.py", "# serves: F-014 — old name\n\n# serves: F-014.c\ndef status():\n    pass\n"
                  "# serves: F-014, P-001\n")
    listing = product.run("tags").output
    assert "shop/orders.py:1  F-014 — old name" in listing and "3 tag(s); 0 code file(s) with none." in listing
    output = product.run("tags", "--refresh").output
    assert "Refreshed 2 tag(s)." in output
    lines = (product.root / "shop/orders.py").read_text().splitlines()
    assert lines[0] == "# serves: F-014 — Track my order"
    assert lines[2].startswith("# serves: F-014.c — Opening someone else's order") and len(lines[2]) <= 100
    assert lines[5] == "# serves: F-014, P-001"


def test_codex_is_reminded_of_each_untagged_file_its_patch_writes(product: Product):
    product.write("charter/features/F-014-track-my-order.md", FEATURE)
    product.write("shop/orders.py", "x = 1\n")
    product.write("shop/gifts.py", "y = 2\n")
    patch = "*** Begin Patch\n*** Add File: shop/orders.py\n+x = 1\n*** Add File: shop/gifts.py\n+y = 2\n*** End Patch"
    result = CliRunner().invoke(main, ["remind"], input=json.dumps(codex(patch, product.root, "PostToolUse")))
    note = json.loads(result.output)["hookSpecificOutput"]["additionalContext"]
    assert "shop/orders.py does not say which feature it serves" in note
    assert "shop/gifts.py does not say which feature it serves" in note
