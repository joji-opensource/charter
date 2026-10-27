# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""One plugin for both agents (0.2): the manifests agree, the hooks match both agents' tools, and the session-start
hook says when the dev-charter command is missing or older than the plugin."""

import json
import subprocess
from pathlib import Path

from dev_charter import __version__

REPO = Path(__file__).resolve().parents[1]
HOOKS = json.loads((REPO / "plugin/hooks/hooks.json").read_text())["hooks"]


def test_claude_code_and_codex_install_the_same_plugin():
    claude = json.loads((REPO / "plugin/.claude-plugin/plugin.json").read_text())
    codex = json.loads((REPO / "plugin/.codex-plugin/plugin.json").read_text())
    assert claude["version"] == codex["version"] == __version__
    assert (codex["skills"], codex["hooks"]) == ("./skills/", "./hooks/hooks.json")
    (entry,) = json.loads((REPO / ".agents/plugins/marketplace.json").read_text())["plugins"]
    assert entry["source"] == {"source": "local", "path": "./plugin"} and entry["policy"]["installation"] == "AVAILABLE"
    assert {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch", "Bash"} == \
        set(HOOKS["PreToolUse"][0]["matcher"].split("|"))
    assert "apply_patch" in HOOKS["PostToolUse"][0]["matcher"].split("|")


def session_start(folder: Path, script: str | None) -> str:
    """What the session-start hook prints when `dev-charter` is the given script, or is not installed."""
    folder.mkdir()
    if script is not None:
        command = folder / "dev-charter"
        command.write_text(script)
        command.chmod(0o755)
    hook = HOOKS["SessionStart"][0]["hooks"][0]["command"]
    done = subprocess.run(["sh", "-c", hook], capture_output=True, text=True, env={"PATH": f"{folder}:/usr/bin:/bin"})
    assert done.returncode == 0
    return done.stdout


def test_session_start_says_when_the_command_is_missing_or_older(tmp_path: Path):
    assert "the dev-charter command is not: uv tool install dev-charter" in session_start(tmp_path / "none", None)
    older = ('#!/bin/sh\ncase "$*" in *--session-start*) echo "No such option: --session-start" >&2; exit 2;; esac\n'
             'echo "Demo Store · mode standard · Dev Charter 0.1.3"\n')
    said = session_start(tmp_path / "older", older)
    assert "older than its plugin: run uv tool upgrade dev-charter" in said and "Demo Store" in said
    current = '#!/bin/sh\necho "Demo Store · mode standard · Dev Charter"\n'
    said = session_start(tmp_path / "current", current)
    assert "older" not in said and "Demo Store" in said
