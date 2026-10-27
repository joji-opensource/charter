# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""How Dev Charter knows its guardrails are running in a coding agent's session.

Before each shell command, the guard notes the command with the agent and the session its hook's payload names, at the
end of a short log of recent commands. A `dev-charter` command run next looks for the note about itself, from its own
session; if there is none, the guard did not run for it: the plugin is missing or older, or Codex has not been told
to trust its hooks. Each agent's shell names its session (`CLAUDE_CODE_SESSION_ID`, `CODEX_THREAD_ID`), the same id
its hooks receive (plan v0.2, probe C13), so two agents in one folder never answer for each other. The variables
alone cannot say which agent is calling (an agent started from another's shell carries both), nor can the processes
above a command (Codex's sandbox forbids reading them); a hook's payload can."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from pathlib import Path

from . import __version__
from .config import LOCAL_DIR

LOG_FILE = "recent-commands.jsonl"
FRESH_SECONDS = 15.0
KEEP_BYTES, KEEP_NOTES = 64 * 1024, 200  # past this size, the log keeps only its newest notes
SESSION_VARIABLES = {"Claude Code": "CLAUDE_CODE_SESSION_ID", "Codex": "CODEX_THREAD_ID"}
AGENT_VARIABLES = ("CLAUDECODE", *SESSION_VARIABLES.values())
GUARDRAILS_OFF = ("Dev Charter's guardrails are not running in this session. In Codex: open /hooks and trust Dev "
                  "Charter's hooks (again after each update). In Claude Code: install the plugin (/plugin install "
                  "dev-charter@dev-charter). If the plugin is installed, it may be older than Dev Charter: update it.")


def agent_of(payload: Mapping) -> str:
    """Which agent sent a hook's payload, from its shape: Codex's carries `turn_id`, Claude Code's `prompt_id`."""
    if "turn_id" in payload:
        return "Codex"
    if "prompt_id" in payload or "/.claude/" in str(payload.get("transcript_path", "")):
        return "Claude Code"
    return "an agent"


def note_command(root: Path, payload: Mapping, command: str) -> None:
    """Add a note to the log. One write in append mode, so notes from two agents at once do not mix."""
    path = root / LOCAL_DIR / LOG_FILE
    note = {"agent": agent_of(payload), "session": payload.get("session_id"), "command": command, "at": time.time()}
    try:
        path.parent.mkdir(exist_ok=True)
        with path.open("a", encoding="utf-8") as log:
            log.write(json.dumps(note) + "\n")
        if path.stat().st_size > KEEP_BYTES:
            temp = path.with_name(f".{LOG_FILE}.{os.getpid()}")
            temp.write_text("".join(path.read_text(encoding="utf-8").splitlines(keepends=True)[-KEEP_NOTES:]),
                            encoding="utf-8")
            temp.replace(path)
    except OSError:
        pass  # without the note, status says the guardrails are not running: the safe way to be wrong


def own_sessions(env: Mapping[str, str] = os.environ) -> set[str]:
    return {value for name in SESSION_VARIABLES.values() if (value := env.get(name))}


def noted(root: Path, words: tuple[str, ...], env: Mapping[str, str] = os.environ) -> dict | None:
    """The guard's note about the command running now: seconds old, about a command with these words, and from this
    command's own session when its shell names one."""
    try:
        lines = (root / LOCAL_DIR / LOG_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    sessions = own_sessions(env)
    now = time.time()
    for line in reversed(lines[-KEEP_NOTES:]):
        try:
            note = json.loads(line)
            fresh = now - float(note["at"]) <= FRESH_SECONDS
        except (ValueError, KeyError, TypeError):
            continue
        if not fresh:
            break
        command = str(note.get("command", ""))
        if all(word in command for word in words) and (not sessions or note.get("session") in sessions):
            return note
    return None


def run_by_an_agent(env: Mapping[str, str] = os.environ) -> bool:
    return any(env.get(name) for name in AGENT_VARIABLES)


def who(root: Path, words: tuple[str, ...], person: str, env: Mapping[str, str] = os.environ) -> str:
    """Who runs the command with these words: the agent the guard noted for it; else the one agent whose variables
    are set (both are set when one agent was started from the other's shell, and then it is "an agent"); else the
    person, by the name given."""
    note = noted(root, words, env)
    if note:
        return str(note["agent"])
    present = [name for name, variables in (("Claude Code", ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID")),
                                            ("Codex", ("CODEX_THREAD_ID",)))
               if any(env.get(v) for v in variables)]
    if present:
        return present[0] if len(present) == 1 else "an agent"
    return person or "a person"


def plugin_version(env: Mapping[str, str] = os.environ) -> str | None:
    """The version of the plugin whose hook is running, from its manifest (both agents give hooks its folder)."""
    folder = env.get("CLAUDE_PLUGIN_ROOT") or env.get("PLUGIN_ROOT")
    if not folder:
        return None
    for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        try:
            return str(json.loads((Path(folder) / manifest).read_text(encoding="utf-8"))["version"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None


def status_lines(root: Path, session_start: bool, env: Mapping[str, str] = os.environ) -> list[str]:
    """What `status` says about the guardrails. At session start no command has been guarded yet, so it says only
    whether the plugin and the command are the same version."""
    if session_start:
        plugin = plugin_version(env)
        if plugin and plugin != __version__:
            return [f"The Dev Charter plugin is {plugin} and the dev-charter command is {__version__}: update the "
                    "older one (uv tool upgrade dev-charter, or the plugin in your coding agent)."]
        return []
    if run_by_an_agent(env) and noted(root, ("dev-charter", "status"), env) is None:
        return [GUARDRAILS_OFF]
    return []
