# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The guard for both agents (0.2): Codex's patches meet Strict mode as Claude Code's edits do; states and sign-offs
are read as Dev Charter reads them; Strict mode keeps its own settings from the agent; a guard that cannot decide
refuses in Strict mode; and each shell command is noted, so `status` knows when the guardrails run."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dev_charter import notes
from dev_charter.cli import main

from .conftest import FEATURE_F014, Product
from .test_edits import ADD, TWO_FILES, codex

FEATURE = FEATURE_F014.replace("decisions: [DEC-001]", "decisions: []")
FEATURE_PATH = "charter/features/F-014-track-my-order.md"
AGENT_VARIABLES = (*notes.AGENT_VARIABLES, "CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT")


def guard(payload: dict | str) -> str | None:
    """Why the guard refuses, or None when it allows."""
    result = CliRunner().invoke(main, ["guard"], input=payload if isinstance(payload, str) else json.dumps(payload))
    assert result.exit_code == 0, result.output
    if not result.output.strip():
        return None
    return json.loads(result.output)["hookSpecificOutput"]["permissionDecisionReason"]


def bash(command: str, root: Path) -> dict:
    return {"session_id": "019a-codex", "turn_id": "019a-turn", "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}, "cwd": str(root)}


def patch(*sections: str) -> str:
    return "*** Begin Patch\n" + "\n".join(sections) + "\n*** End Patch"


def update(rel: str, *lines: str) -> str:
    return f"*** Update File: {rel}\n@@\n" + "\n".join(lines)


@pytest.fixture
def shop(git_product: Product) -> Product:
    """A store in Strict mode with feature F-014 and one open card allowed to change shop/orders/."""
    git_product.write(FEATURE_PATH, FEATURE)
    git_product.run("card", "new", "Order page", "--serves", "F-014.a")
    card = next((git_product.root / "charter/cards").glob("CARD-001-*.md"))
    card.write_text(card.read_text().replace("## Allowed paths\n", "## Allowed paths\n\n- shop/orders/**\n"))
    git_product.run("strict", "on")
    return git_product


def test_codex_patches_meet_strict_mode_as_claude_codes_edits_do(shop: Product):
    root = shop.root
    outside = patch("*** Add File: shop/gifts/card.py\n+y = 2")
    assert "shop/gifts/card.py is not in the allowed paths of an open task card" in guard(codex(outside, root))
    assert guard(codex(ADD, root)) is None
    assert "shop/gifts/b.py is not in the allowed paths" in guard(codex(TWO_FILES, root)), "one file refuses all"

    signed = " - 2026-10-24 · b · Joji John · received the text on a real phone during a staging order"
    sign_off = patch(update(FEATURE_PATH, signed, "+- 2026-10-27 · a · Codex · saw the order page"))
    assert "only a person adds a sign-off" in guard(codex(sign_off, root))
    state = patch(update(FEATURE_PATH, "-state: agreed", "+state: live"))
    assert "only a person changes a feature's or a promise's state" in guard(codex(state, root))
    wording = patch(update(FEATURE_PATH, "-**I want to** see where my order is and when it will arrive",
                           "+**I want to** see where each order is and when it will arrive"))
    assert guard(codex(wording, root)) is None
    moved = f"*** Update File: {FEATURE_PATH}\n*** Move to: charter/features/F-099-x.md\n@@\n state: agreed"
    for gone in (f"*** Delete File: {FEATURE_PATH}", moved):
        assert "only a person deletes, moves or renames" in guard(codex(patch(gone), root))
    blank = patch(update(FEATURE_PATH, " ", "+**Note** hello"))
    assert "could not check this change to charter/features/F-014" in guard(codex(blank, root))


def test_states_and_sign_offs_are_read_as_dev_charter_reads_them(shop: Product):
    feature = str(shop.root / FEATURE_PATH)
    twice = {"tool_name": "Write", "tool_input": {
        "file_path": feature, "content": FEATURE.replace("state: agreed\n", 'state: agreed\n"state": live\n')}}
    assert ("could not read charter/features/F-014-track-my-order.md after it. The details could not be read: 'state' "
            "is written twice.") in guard(twice)
    indented = {"tool_name": "Edit", "tool_input": {
        "file_path": feature, "old_string": "## Sign-offs\n",
        "new_string": "## Sign-offs\n\n  - 2026-10-27 · a · Claude · looked fine\n"}}
    assert "only a person adds a sign-off" in guard(indented)
    deleted = {"tool_name": "Edit", "tool_input": {"file_path": feature, "old_string": "state: agreed\n",
                                                   "new_string": ""}}
    assert "only a person changes a feature's or a promise's state" in guard(deleted)


def test_strict_mode_keeps_its_own_settings_from_the_agent(shop: Product):
    root = shop.root
    for rel in ("charter.toml", ".dev-charter/strict"):
        edit = {"tool_name": "Write", "tool_input": {"file_path": str(root / rel), "content": "x"}}
        assert "only a person changes them" in guard(edit)
    for command in ("rm .dev-charter/strict", "cat charter.toml",
                    "dev-charter status --brief && rm .dev-charter/strict"):
        assert "only a person changes them" in guard(bash(command, root)), command
    assert "only a person turns Strict mode off" in guard(bash("dev-charter strict off", root))
    assert guard(bash("dev-charter status --brief", root)) is None
    assert guard(bash("dev-charter strict on --hours 2", root)) is None
    shop.run("strict", "off")
    assert guard(bash("rm .dev-charter/strict", root)) is None, "outside Strict mode there is nothing to keep"


def test_a_guard_that_cannot_decide_refuses_in_strict_mode_only(shop: Product, monkeypatch: pytest.MonkeyPatch):
    root = shop.root
    broken = codex(ADD.removesuffix("\n*** End Patch"), root)
    assert "could not read this change (the patch has no '*** End Patch' line)" in guard(broken)
    monkeypatch.chdir(root)
    assert "could not read this tool call" in guard("this is not JSON")
    shop.run("strict", "off")
    assert guard(broken) is None and guard("this is not JSON") is None

    (root / ".dev-charter/strict").write_text("whenever")
    assert "Strict until a person turns it off" in shop.run("status", "--brief").output
    assert "not in the allowed paths" in guard(codex(patch("*** Add File: shop/gifts/card.py\n+y = 2"), root))
    (root / ".dev-charter/strict").unlink()

    toml = root / "charter.toml"
    toml.write_text(toml.read_text() + "\nthis is [not toml\n")
    assert "charter.toml cannot be read" in guard(codex(ADD, root)), "in every mode"
    assert guard({"tool_name": "Write", "tool_input": {"file_path": str(toml), "content": "x"}}) is None


def test_status_says_when_the_guard_did_not_see_its_own_command(git_product: Product,
                                                                monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    for name in AGENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    root = git_product.root
    assert notes.GUARDRAILS_OFF not in git_product.run("status", "--brief").output, "a person at a terminal"
    monkeypatch.setenv("CODEX_THREAD_ID", "019a-codex")
    assert notes.GUARDRAILS_OFF in git_product.run("status", "--brief").output, "an agent the guard did not see"

    assert guard(bash("dev-charter status --brief", root)) is None
    assert notes.GUARDRAILS_OFF not in git_product.run("status", "--brief").output
    log = root / ".dev-charter" / notes.LOG_FILE
    (seen,) = [json.loads(line) for line in log.read_text().splitlines()]
    assert (seen["agent"], seen["session"]) == ("Codex", "019a-codex")
    log.write_text(json.dumps({**seen, "at": seen["at"] - 60}) + "\n")
    assert notes.GUARDRAILS_OFF in git_product.run("status", "--brief").output, "a note about an earlier command"

    start = git_product.run("status", "--brief", "--session-start").output
    assert notes.GUARDRAILS_OFF not in start, "no command has been guarded yet at session start"
    plugin = tmp_path / "plugin"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin/plugin.json").write_text(json.dumps({"version": "9.9.9"}))
    monkeypatch.setenv("PLUGIN_ROOT", str(plugin))
    assert "The Dev Charter plugin is 9.9.9 and the dev-charter command is" in \
        git_product.run("status", "--brief", "--session-start").output


def test_two_agents_in_one_folder_never_answer_for_each_other(git_product: Product, monkeypatch: pytest.MonkeyPatch):
    for name in AGENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    root = git_product.root
    claude = {**bash("dev-charter status --brief", root), "session_id": "cc6f-claude"}
    del claude["turn_id"]
    claude["prompt_id"] = "p1"
    assert guard(claude) is None  # Claude Code's guard sees its status command
    for command in ("ls", "pytest -q", "git diff"):  # then Codex runs commands of its own
        assert guard(bash(command, root)) is None

    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "cc6f-claude")
    assert notes.GUARDRAILS_OFF not in git_product.run("status", "--brief").output, "its own note, despite newer ones"
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID")
    monkeypatch.setenv("CODEX_THREAD_ID", "019a-other")  # a third session, whose guard did not run
    assert notes.GUARDRAILS_OFF in git_product.run("status", "--brief").output, "never satisfied by another's note"


def test_the_log_of_recent_commands_stays_small(git_product: Product):
    root = git_product.root
    for number in range(notes.KEEP_BYTES // 100):
        notes.note_command(root, {"session_id": "s", "turn_id": "t"}, f"echo {number} " + "x" * 80)
    path = root / ".dev-charter" / notes.LOG_FILE
    assert path.stat().st_size <= notes.KEEP_BYTES + 200, "trimmed to its newest notes whenever it grows past the limit"
    assert json.loads(path.read_text().splitlines()[-1])["command"].startswith("echo 654 ")
