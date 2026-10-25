# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Team work on branches (stage 2b), Strict mode (stage 3) and the pull-request summary and ledger (stage 4)."""

import json
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner
from openpyxl import load_workbook

from dev_charter import ci, config, publish, strict
from dev_charter.cli import main

from .conftest import FEATURE_F014, Product

FEATURE = FEATURE_F014.replace("decisions: [DEC-001]", "decisions: []").replace(
    "\n- 2026-10-24 · b · Joji John · received the text on a real phone during a staging order\n", "\n")


def clone(remote: Path, where: Path, name: str) -> Product:
    subprocess.run(["git", "clone", "-q", str(remote), str(where)], check=True, capture_output=True)
    person = Product(where)
    person.git("config", "user.email", f"{name.lower()}@example.com")
    person.git("config", "user.name", name)
    return person


def shared_product(tmp_path: Path) -> tuple[Path, Product, Product]:
    """A product on a shared remote, cloned by Alice and Bob."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    alice = clone(remote, tmp_path / "alice", "Alice")
    alice.run("init", "--name", "Shop", "--role", "customer", "--yes")
    alice.commit("set up Dev Charter")
    alice.git("push", "-q", "origin", "main")
    bob = clone(remote, tmp_path / "bob", "Bob")
    bob.run("sync")
    return remote, alice, bob


def created_id(result) -> str:
    return result.output.split("Created ")[1].split(" ")[0]


def test_F_ids_do_not_collide_once_a_teammate_has_fetched(tmp_path: Path):
    _, alice, bob = shared_product(tmp_path)
    alice.git("checkout", "-q", "-b", "gift-wrapping")
    assert created_id(alice.run("feature", "new", "Gift wrapping")) == "F-001"
    alice.commit("gift wrapping")
    alice.git("push", "-q", "origin", "gift-wrapping")

    bob.git("fetch", "-q")
    bob.git("checkout", "-q", "-b", "order-notes")
    assert created_id(bob.run("feature", "new", "Order notes")) == "F-002"


def test_an_id_is_never_reused_after_its_file_is_deleted(git_product: Product):
    git_product.run("feature", "new", "Gift wrapping")
    git_product.commit("gift wrapping")
    git_product.git("rm", "-q", "charter/features/F-001-gift-wrapping.md")
    git_product.commit("drop gift wrapping")
    assert created_id(git_product.run("feature", "new", "Order notes")) == "F-002"


JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="1">
  <testcase classname="tests.test_shop" name="test_F401_a_shows_the_step"/>
</testsuite></testsuites>
"""


def test_renumber_moves_every_reference_and_leaves_lint_codes_alone(git_product: Product):
    shop = git_product
    shop.write("charter/features/F-401-track-my-order.md", FEATURE.replace("id: F-014", "id: F-401"))
    shop.write("charter/decisions/DEC-001-dates.md", "---\nid: DEC-001\ntitle: Dates\nfeatures: [F-401]\n---\n\n"
               "**Decision** Use the carrier's date for F-401.\n**Because** Customers trust it.\n")
    shop.run("card", "new", "Order page", "--serves", "F-401.a")
    shop.write("shop/orders.py", "# serves: F-401\ndef step(order):\n    return order['step']\n")
    shop.write("tests/test_shop.py", "import os  # noqa: F401\n\n\ndef test_F401_a_shows_the_step():\n"
               "    assert True\n")
    shop.set_results("reports/*.xml")
    shop.write("reports/junit.xml", JUNIT)

    output = shop.run("renumber", "F-401").output
    assert "Renumbered F-401 to F-402" in output
    root = shop.root
    assert (root / "charter/features/F-402-track-my-order.md").read_text().startswith("---\nid: F-402\n")
    assert not (root / "charter/features/F-401-track-my-order.md").exists()
    assert "features: [F-402]" in (root / "charter/decisions/DEC-001-dates.md").read_text()
    assert "Use the carrier's date for F-402." in (root / "charter/decisions/DEC-001-dates.md").read_text()
    assert 'serves: ["F-402.a"]' in next((root / "charter/cards").glob("CARD-001-*.md")).read_text()
    assert (root / "shop/orders.py").read_text().startswith("# serves: F-402\n")
    tests = (root / "tests/test_shop.py").read_text()
    assert "def test_F402_a_shows_the_step():" in tests
    assert "import os  # noqa: F401" in tests  # probe T3: a lint code is not an ID
    assert "tests/test_shop.py:1  import os  # noqa: F401" in output
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--junitxml=reports/junit.xml",
                    "tests"], cwd=root, check=True, capture_output=True)
    assert "0 problem(s)" in shop.run("check").output


def test_an_id_that_was_ever_used_cannot_be_taken(git_product: Product):
    git_product.run("feature", "new", "Gift wrapping")
    git_product.run("feature", "new", "Order notes")
    git_product.commit("two features")
    result = git_product.run("renumber", "F-002", "--to", "F-001", ok=False)
    assert result.exit_code == 1 and "has already been used" in result.output


def test_two_branches_park_ideas_and_write_handoffs_without_conflicts(git_product: Product):
    shop = git_product
    shop.git("checkout", "-q", "-b", "alice")
    shop.run("card", "new", "Gift wrapping")
    shop.run("park", "Gift cards", "--from", "Alice")
    card = next((shop.root / "charter/cards").glob("CARD-001-*.md"))
    card.write_text(card.read_text().replace("- Next step:", "- Next step: wrap the gift"))
    shop.commit("alice", check=False)
    shop.git("checkout", "-q", "main")
    shop.git("checkout", "-q", "-b", "bob")
    assert created_id(shop.run("card", "new", "Order notes")) == "CARD-002"
    shop.run("park", "Export order history", "--from", "Bob")
    card = next((shop.root / "charter/cards").glob("CARD-002-*.md"))
    card.write_text(card.read_text().replace("- Next step:", "- Next step: save the note"))
    shop.commit("bob", check=False)

    shop.git("checkout", "-q", "main")
    shop.git("merge", "-q", "--no-edit", "alice")
    merged = shop.git("merge", "--no-edit", "bob", check=False)
    assert merged.returncode == 0, merged.stdout + merged.stderr
    ideas = (shop.root / "charter/ideas.md").read_text()
    assert "Gift cards" in ideas and "Export order history" in ideas


def test_work_on_other_branches_is_listed_before_it_merges(git_product: Product):
    shop = git_product
    shop.write("charter/features/F-014-track-my-order.md", FEATURE)
    shop.commit("feature")
    shop.git("checkout", "-q", "-b", "alice/order-page")
    shop.run("card", "new", "Order page", "--serves", "F-014.a")
    card = next((shop.root / "charter/cards").glob("CARD-001-*.md"))
    card.write_text(card.read_text().replace("- Next step:", "- Next step: show the carrier's date"))
    shop.commit("order page card", check=False)
    shop.git("checkout", "-q", "main")

    brief = shop.run("status", "--brief").output
    assert "Work in progress on other branches (not yet merged into main):" in brief
    assert "alice/order-page (Test" in brief and "CARD-001 Order page (F-014.a)" in brief
    shop.run("report")
    wip = load_workbook(shop.root / "LEDGER.xlsx")["Work in progress"]
    assert [c.value for c in wip[3]][:1] + [c.value for c in wip[3]][5:9] == [
        "alice/order-page", "CARD-001", "Order page", "F-014.a", "show the carrier's date"]

    shop.git("merge", "-q", "--no-edit", "alice/order-page")
    assert "Work in progress on other branches" not in shop.run("status", "--brief").output


def test_the_product_owner_approves_product_changes(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    Product(tmp_path).run("init", "--owner", "po-name", "--yes")
    owners = (tmp_path / ".github/CODEOWNERS").read_text()
    for folder in ("features", "promises", "decisions"):
        assert f"/charter/{folder}/ @po-name" in owners
    assert "cards" not in owners


def guard(payload: dict) -> dict | None:
    result = CliRunner().invoke(main, ["guard"], input=json.dumps(payload))
    assert result.exit_code == 0
    return json.loads(result.output) if result.output.strip() else None


def test_strict_mode_keeps_claude_inside_its_card(git_product: Product):
    shop = git_product
    shop.write("charter/features/F-014-track-my-order.md", FEATURE)
    shop.run("card", "new", "Order page", "--serves", "F-014.a")
    card = next((shop.root / "charter/cards").glob("CARD-001-*.md"))
    card.write_text(card.read_text().replace("## Allowed paths\n", "## Allowed paths\n\n- shop/orders/**\n"))
    edit = {"tool_name": "Edit", "tool_input": {"file_path": str(shop.root / "shop/payments.py"),
                                                "old_string": "a", "new_string": "b"}}
    assert guard(edit) is None  # standard mode: no guard

    assert "Strict mode is on" in shop.run("strict", "on").output
    denied = guard(edit)["hookSpecificOutput"]
    assert denied["permissionDecision"] == "deny"
    assert "shop/payments.py is not in the allowed paths of an open task card (CARD-001: shop/orders/**)" in \
        denied["permissionDecisionReason"]
    allowed = {**edit, "tool_input": {**edit["tool_input"], "file_path": str(shop.root / "shop/orders/status.py")}}
    assert guard(allowed) is None

    feature = str(shop.root / "charter/features/F-014-track-my-order.md")
    sign_off = {"tool_name": "Edit", "tool_input": {
        "file_path": feature, "old_string": "## Sign-offs\n",
        "new_string": "## Sign-offs\n\n- 2026-10-25 · proven · Claude · looked fine\n"}}
    assert "only a person adds a sign-off" in guard(sign_off)["hookSpecificOutput"]["permissionDecisionReason"]
    state = {"tool_name": "Edit", "tool_input": {"file_path": feature, "old_string": "state: agreed",
                                                 "new_string": "state: live"}}
    assert "only a person changes" in guard(state)["hookSpecificOutput"]["permissionDecisionReason"]
    wording = {"tool_name": "Edit", "tool_input": {"file_path": feature, "old_string": "see where my order is",
                                                   "new_string": "see where each order is"}}
    assert guard(wording) is None

    assert "Strict until" in shop.run("status", "--brief").output
    shop.run("strict", "off")
    assert guard(edit) is None
    assert strict.strict_until(config.load(shop.root)) is None


def test_the_pull_request_summary_speaks_plainly_and_refuses_a_reused_id(git_product: Product):
    shop = git_product
    shop.write("charter/features/F-014-track-my-order.md", FEATURE)
    shop.commit("feature")
    shop.git("checkout", "-q", "-b", "work")
    feature = shop.root / "charter/features/F-014-track-my-order.md"
    feature.write_text(feature.read_text().replace("state: agreed", "state: live").replace(
        "## Sign-offs\n", "## Sign-offs\n\n- 2026-10-25 · proven · Joji John · watched it on staging\n"))
    shop.run("feature", "new", "Gift wrapping")
    shop.write("shop/gifts.py", "def wrap(order):\n    return order\n")
    shop.commit("work", check=False)

    result = shop.run("pr-summary", "--base", "main", ok=False)
    assert "**New feature F-015:** Gift wrapping (idea" in result.output
    assert "F-014 Track my order:** state agreed → live; signed off (proven) by Joji John" in result.output
    assert "This new code file does not say which feature it serves" in result.output
    assert result.exit_code == 1

    shop.write("shop/gifts.py", "# serves: F-015\ndef wrap(order):\n    return order\n")
    shop.commit("tag", check=False)
    assert "Nothing to fix" in shop.run("pr-summary", "--base", "main").output

    shop.write("charter/features/F-014-gift-cards.md", FEATURE.replace("Track my order", "Gift cards"))
    shop.commit("reuse", check=False)
    reused = shop.run("pr-summary", "--base", "main", ok=False)
    assert reused.exit_code == 1
    assert "F-014 is also used by" in reused.output or "F-014 is already used on main" in reused.output


def test_the_ledger_is_published_on_its_own_branch(git_product: Product):
    git_product.write("charter/features/F-014-track-my-order.md", FEATURE)
    git_product.commit("feature")
    git_product.run("report")
    cfg = config.load(git_product.root)
    first = publish.publish(cfg, push=False)
    second = publish.publish(cfg, push=False)
    files = git_product.git("ls-tree", "--name-only", "ledger").stdout.split()
    assert files == ["LEDGER.xlsx", "README.md", "status.html"]
    assert git_product.git("rev-parse", f"{second}^").stdout.strip() == first


def test_the_workflow_runs_the_tests_and_keeps_the_ledger(git_product: Product):
    git_product.write("pyproject.toml", "[project]\nname = 'shop'\nversion = '0.1.0'\n")
    output = git_product.run("ci").output
    assert ".github/workflows/dev-charter.yml: created" in output
    text = (git_product.root / ci.WORKFLOW).read_text()
    assert "branches: [main]" in text
    assert "uv run pytest --junitxml=reports/junit.xml" in text
    assert 'dev-charter pr-summary --base "origin/${{ github.base_ref }}" --comment' in text
    assert "dev-charter report && dev-charter publish" in text
    assert ".github/workflows/dev-charter.yml: unchanged" in git_product.run("ci").output
