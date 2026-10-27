# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Reading both agents' edits (0.2): Claude Code's edit tools, and Codex's patches in the shapes Codex 0.164 sends
(captured in probe C1 of the v0.2 plan)."""

from pathlib import Path

import pytest

from dev_charter import edits, notes

ADD = "*** Begin Patch\n*** Add File: shop/orders/eta.py\n+# serves: foundation\n+x = 1\n*** End Patch"
UPDATE = "*** Begin Patch\n*** Update File: shop/orders/eta.py\n@@\n-x = 1\n+x = 2\n*** End Patch"
MOVE = ("*** Begin Patch\n*** Update File: shop/orders/eta.py\n*** Move to: shop/orders/when.py\n@@\n"
        " # serves: foundation\n x = 2\n*** End Patch")
DELETE = "*** Begin Patch\n*** Delete File: shop/orders/when.py\n*** End Patch"
TWO_FILES = ("*** Begin Patch\n*** Add File: shop/orders/a.py\n+# serves: foundation\n"
             "*** Add File: shop/gifts/b.py\n+# serves: foundation\n*** End Patch")


def codex(patch: str, root: Path, event: str = "PreToolUse") -> dict:
    """A Codex hook payload, as Codex 0.164 sends it."""
    return {"session_id": "019a-codex", "turn_id": "019a-turn", "model": "gpt", "hook_event_name": event,
            "tool_name": "apply_patch", "tool_input": {"command": patch}, "cwd": str(root),
            "permission_mode": "default", "tool_use_id": "call_1", "transcript_path": "/home/x/.codex/sessions/s.jsonl"}


def test_codex_patches_are_read_file_by_file(tmp_path: Path):
    (add,) = edits.changes(codex(ADD, tmp_path), tmp_path)
    assert (add.op, add.path, add.added) == ("add", tmp_path / "shop/orders/eta.py", ("# serves: foundation", "x = 1"))
    (update,) = edits.changes(codex(UPDATE, tmp_path), tmp_path)
    assert update.op == "update" and update.hunks == (edits.Hunk("", ("x = 1",), ("x = 2",)),)
    (move,) = edits.changes(codex(MOVE, tmp_path), tmp_path)
    assert (move.path, move.to) == (tmp_path / "shop/orders/eta.py", tmp_path / "shop/orders/when.py")
    (delete,) = edits.changes(codex(DELETE, tmp_path), tmp_path)
    assert delete.op == "delete"
    assert [c.path.name for c in edits.changes(codex(TWO_FILES, tmp_path), tmp_path)] == ["a.py", "b.py"]


def test_a_patch_dev_charter_cannot_read_says_why(tmp_path: Path):
    for broken, why in ((ADD.removesuffix("\n*** End Patch"), "no '\\*\\*\\* End Patch' line"),
                        (ADD.replace("*** Add File", "*** Rename File"), "not one Dev Charter knows"),
                        ("*** Begin Patch\n*** End Patch", "changes no file")):
        with pytest.raises(edits.UnreadableEdit, match=why):
            edits.changes(codex(broken, tmp_path), tmp_path)
    with pytest.raises(edits.UnreadableEdit, match="names no file"):
        edits.changes({"tool_name": "Edit", "tool_input": {}}, tmp_path)


def test_claude_codes_tools_shell_commands_and_patches_inside_them(tmp_path: Path):
    write = {"tool_name": "Write", "tool_input": {"file_path": "shop/x.py", "content": "a"}, "cwd": str(tmp_path)}
    assert edits.changes(write, tmp_path) == [edits.Change("edit", tmp_path / "shop/x.py")]
    notebook = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": str(tmp_path / "n.ipynb")}}
    assert edits.changes(notebook, tmp_path)[0].path == tmp_path / "n.ipynb"
    assert edits.changes({"tool_name": "Read", "tool_input": {"file_path": "x"}}, tmp_path) == []
    bash = {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}
    assert edits.shell_command(bash) == "ls -la" and edits.changes(bash, tmp_path) == []
    heredoc = {"tool_name": "Bash", "tool_input": {"command": f"apply_patch <<'EOF'\n{DELETE}\nEOF"},
               "cwd": str(tmp_path)}
    assert edits.changes(heredoc, tmp_path)[0].op == "delete"


def test_a_patch_is_placed_only_where_it_fits_once():
    text = "a\nb\nc\nb\nd\n"
    assert edits.apply_hunks(text, (edits.Hunk("", ("a", "b"), ("a", "B")),)) == "a\nB\nc\nb\nd\n"
    assert edits.apply_hunks(text, (edits.Hunk("c", ("b",), ("B",)),)) == "a\nb\nc\nB\nd\n"
    with pytest.raises(edits.UnreadableEdit, match="fits 2 places"):
        edits.apply_hunks(text, (edits.Hunk("", ("b",), ("B",)),))
    with pytest.raises(edits.UnreadableEdit, match="fits 0 places"):
        edits.apply_hunks(text, (edits.Hunk("", ("z",), ("y",)),))
    (add,) = edits.changes(codex(ADD, Path("/p")), Path("/p"))
    assert edits.text_after(add, {}, "") == "# serves: foundation\nx = 1\n"


def test_which_agent_a_payload_comes_from(tmp_path: Path):
    assert notes.agent_of(codex(ADD, tmp_path)) == "Codex"
    claude = {"session_id": "cc6f", "prompt_id": "p1", "effort": "high",
              "transcript_path": "/u/.claude/projects/x.jsonl"}
    assert notes.agent_of(claude) == "Claude Code"
    assert notes.agent_of({"session_id": "s"}) == "an agent"
