# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Taking turns (0.2): each turn on a card says when, which agent (or person) and what it did, so a card handed between
Claude Code and Codex shows who did which stage."""

import re

import pytest

from dev_charter import agents, store
from dev_charter.config import find_root, load

from .conftest import Product
from .test_guard import AGENT_VARIABLES, bash, guard

TURN_RE = re.compile(r"^- \d{4}-\d{2}-\d{2} \d{2}:\d{2} · (?P<who>[^·]+) · (?P<did>.+)$")


@pytest.fixture
def shop(git_product: Product, monkeypatch: pytest.MonkeyPatch) -> Product:
    for name in AGENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    git_product.run("card", "new", "Order page")
    return git_product


def turns(shop: Product) -> list[tuple[str, str]]:
    text = next((shop.root / "charter/cards").glob("CARD-001-*.md")).read_text()
    return [(m["who"], m["did"]) for line in text.splitlines() if (m := TURN_RE.match(line))]


def test_a_card_handed_between_agents_shows_each_turn_in_order(shop: Product, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    shop.run("card", "turn", "CARD-001", "--did", "planned")
    monkeypatch.delenv("CLAUDECODE")
    monkeypatch.setenv("CODEX_THREAD_ID", "019a-codex")
    said = shop.run("card", "turn", "CARD-001", "--did", "review pass 2").output
    assert re.match(r"Recorded on CARD-001: \d{4}-\d{2}-\d{2} \d{2}:\d{2} · Codex · review pass 2", said)
    monkeypatch.delenv("CODEX_THREAD_ID")
    shop.run("card", "turn", "CARD-001", "--did", "agreed · the plan")
    assert turns(shop) == [("Claude Code", "planned"), ("Codex", "review pass 2"), ("Test", "agreed - the plan")]
    assert "0 problem(s)" in shop.run("check").output


def test_the_guards_note_names_the_agent_even_when_both_agents_variables_are_set(shop: Product,
                                                                                 monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CODEX_THREAD_ID", "019a-codex")  # Codex started from Claude Code's shell
    shop.run("card", "turn", "CARD-001", "--did", "without the plugin")
    command = 'dev-charter card turn CARD-001 --did "review pass 2"'
    assert guard(bash(command, shop.root)) is None  # Codex's hook sees the command first
    shop.run("card", "turn", "CARD-001", "--did", "review pass 2")
    assert turns(shop) == [("an agent", "without the plugin"), ("Codex", "review pass 2")]


def test_an_older_card_gets_the_section_and_nothing_else_changes(shop: Product):
    path = next((shop.root / "charter/cards").glob("CARD-001-*.md"))
    text = path.read_text()
    older = text[: text.index("## Turns")].rstrip() + "\n"
    path.write_text(older)
    shop.run("card", "turn", "CARD-001", "--did", "built")
    after = path.read_text()
    assert after.startswith(older.rstrip() + "\n\n## Turns\n\n- ")
    card = store.read_card(path)
    assert (card.id, card.title, card.state) == ("CARD-001", "Order page", "open")
    assert "0 problem(s)" in shop.run("check").output


def test_a_turn_needs_a_card_and_words(shop: Product):
    assert "There is no task card CARD-009" in shop.run("card", "turn", "CARD-009", "--did", "x", ok=False).output
    assert "'*' is not a task card ID" in shop.run("card", "turn", "*", "--did", "x", ok=False).output
    assert "Say what the turn did" in shop.run("card", "turn", "CARD-001", "--did", " ", ok=False).output


def test_the_rules_ask_for_a_turn_and_stay_short(shop: Product):
    block = agents.render_block()
    assert 'dev-charter card turn CARD-nnn --did "<what you did>"' in block
    assert len(block.splitlines()) <= 40
    assert agents.block_state(load(find_root(shop.root)).root)[0] == agents.CURRENT
