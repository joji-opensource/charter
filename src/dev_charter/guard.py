# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The guard a coding agent's hook runs before each edit and shell command, for Claude Code and Codex alike.

In Strict mode it keeps the agent to the open task cards' allowed paths, away from sign-offs and states, and away from
the settings that hold Strict mode itself; when it cannot tell whether a change is allowed, it refuses. In every mode
it notes each shell command, so `status` can tell whether the guardrails are running (`notes.py`). It is a guardrail
for an agent that follows its rules, not a wall: a shell command can still change a file."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

from . import edits, notes
from .config import CHARTER_DIR, CONFIG_FILE, LOCAL_DIR, Config, find_root, load
from .errors import CharterError, FileProblem
from .model import FEATURE, PROMISE, Kind
from .scan import matches
from .store import Parsed, open_cards, parse

STRICT_FILE = "strict"
FOREVER = datetime.max  # Strict mode whose end cannot be read stays on until a person turns it off
ENTRY_FOLDERS = {f"{CHARTER_DIR}/{FEATURE.folder}/": FEATURE, f"{CHARTER_DIR}/{PROMISE.folder}/": PROMISE}
STRICT_OFF_RE = re.compile(r"\bdev-charter\b.*\bstrict\s+off\b")
SETTINGS_RE = re.compile(r"\.dev-charter\b|\bcharter\.toml\b")
DEV_CHARTER_ONLY_RE = re.compile(r"^\s*(\S*/)?dev-charter(\s|$)")
SHELL_JOIN_RE = re.compile(r"[;&|`<>\n]|\$\(")
SETTINGS = ("Strict mode: charter.toml and .dev-charter/ hold this product's settings and Strict mode itself, and only "
            "a person changes them. Ask the person.")


def strict_until(config: Config) -> datetime | None:
    """Until when Strict mode was turned on for this clone, if it still is; `FOREVER` if that cannot be read."""
    path = config.root / LOCAL_DIR / STRICT_FILE
    if not path.is_file():
        return None
    try:
        until = datetime.fromisoformat(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return FOREVER
    return until if until > datetime.now() else None


def is_strict(config: Config) -> bool:
    return config.mode == "strict" or strict_until(config) is not None


def turn_on(config: Config, hours: float) -> datetime:
    until = datetime.now() + timedelta(hours=hours)
    folder = config.root / LOCAL_DIR
    folder.mkdir(exist_ok=True)
    (folder / STRICT_FILE).write_text(until.isoformat(timespec="minutes"), encoding="utf-8")
    return until


def turn_off(config: Config) -> None:
    (config.root / LOCAL_DIR / STRICT_FILE).unlink(missing_ok=True)


def decide(payload: dict, cwd: Path) -> str | None:
    """Why this edit or shell command is refused, or None when it may go ahead."""
    cwd = Path(payload.get("cwd") or cwd)
    command = edits.shell_command(payload)
    unreadable = None
    try:
        found = edits.changes(payload, cwd)
    except edits.UnreadableEdit as exc:
        found, unreadable = [], str(exc)
    if command is None and not found and unreadable is None:
        return None  # neither an edit nor a command
    try:
        root = find_root(found[0].path.parent if found else cwd)
    except CharterError:
        return None  # not inside a product Dev Charter manages
    try:
        config = load(root)
    except CharterError as exc:
        if command is not None or (found and all(_relative(root, c.path) == CONFIG_FILE and not c.to for c in found)):
            return None
        return f"{CONFIG_FILE} cannot be read ({exc}), so Dev Charter cannot tell what is allowed. Fix it first."
    if command is not None:
        notes.note_command(root, payload, command)
    if not is_strict(config):
        return None
    try:
        if command is not None and (reason := _command(command)):
            return reason
        if unreadable is not None:
            return (f"Strict mode: Dev Charter could not read this change ({unreadable}), so it is refused. Make it "
                    "as a patch of one file, or ask the person.")
        for change in found:
            if reason := _change(config, change, payload):
                return reason
        return None
    except Exception as exc:  # in Strict mode, a guard that cannot decide refuses
        return f"Strict mode: Dev Charter could not check this change ({exc}), so it is refused. Ask the person."


def unreadable(cwd: Path, why: str) -> str | None:
    """A hook call that cannot be read at all: refused in Strict mode, allowed otherwise, as any guard failure."""
    try:
        config = load(find_root(cwd))
    except CharterError:
        return None
    if not is_strict(config):
        return None
    return f"Strict mode: Dev Charter could not read this tool call ({why}), so it is refused. Ask the person."


def _relative(root: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _command(command: str) -> str | None:
    if STRICT_OFF_RE.search(command):
        return "Strict mode: only a person turns Strict mode off, from their own terminal."
    if SETTINGS_RE.search(command) and (not DEV_CHARTER_ONLY_RE.match(command) or SHELL_JOIN_RE.search(command)):
        return SETTINGS
    return None


def _change(config: Config, change: edits.Change, payload: dict) -> str | None:
    for path in (change.path, change.to):
        relative = None if path is None else _relative(config.root, path)
        if relative is None:
            continue
        if relative in (CONFIG_FILE, LOCAL_DIR) or relative.startswith(f"{LOCAL_DIR}/"):
            return SETTINGS
        kind = next((k for folder, k in ENTRY_FOLDERS.items() if relative.startswith(folder)), None)
        if kind is not None:
            if change.op == "delete" or change.to is not None:
                return "Strict mode: only a person deletes, moves or renames a feature or a promise."
            return _entry(path, relative, kind, change, payload)
        if relative.startswith(f"{CHARTER_DIR}/"):
            continue
        if reason := _card_paths(config, relative):
            return reason
    return None


def _entry(path: Path, relative: str, kind: Kind, change: edits.Change, payload: dict) -> str | None:
    """A change to a feature or a promise, read before and after as Dev Charter reads it everywhere else."""
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    try:
        after = edits.text_after(change, payload, current) or ""
    except edits.UnreadableEdit as exc:
        return (f"Strict mode: Dev Charter could not check this change to {relative} ({exc}), so it is refused. "
                "Make it with more lines around it, or ask the person.")
    try:
        before = parse(path, kind, current) if current else None
    except FileProblem:
        return f"Strict mode: {relative} cannot be read as it is, so a change to it cannot be checked. Ask the person."
    try:
        proposed = parse(path, kind, after)
    except FileProblem as problem:
        return (f"Strict mode: this change is refused, because Dev Charter could not read {relative} after it. "
                f"{problem.message}")
    if _signoffs(proposed) - _signoffs(before):
        return "Strict mode: only a person adds a sign-off. Tell the person what to check and let them sign it off."
    if before is not None and _state(before) != _state(proposed):
        return "Strict mode: only a person changes a feature's or a promise's state."
    return None


def _signoffs(parsed: Parsed | None) -> set[str]:
    if parsed is None:
        return set()
    return {raw.strip() for _, raw in parsed.sections.get("Sign-offs", []) if raw.strip().startswith("-")}


def _state(parsed: Parsed) -> str:
    return str(parsed.meta.get("state") or "")


def _card_paths(config: Config, relative: str) -> str | None:
    cards = open_cards(config)
    if any(matches(relative, card.allowed) for card in cards if card.allowed):
        return None
    if not cards:
        return (f"Strict mode: {relative} can only change for an open task card. Make one with `dev-charter card "
                "new`, list the files it may change under '## Allowed paths', then try again.")
    allowed = "; ".join(f"{c.id}: {', '.join(c.allowed) or 'no paths listed'}" for c in cards)
    return (f"Strict mode: {relative} is not in the allowed paths of an open task card ({allowed}). If a check on "
            "the card cannot pass without it, follow the blocker test in `dev-charter guide build` and add it to the "
            "card's Allowed paths; otherwise park the idea with `dev-charter park`.")
