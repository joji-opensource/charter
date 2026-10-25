# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Strict mode: Claude Code may change only what the open task cards allow, and never a sign-off or a state."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

from .config import CHARTER_DIR, Config, find_root, load
from .errors import CharterError
from .model import CARD, FEATURE, PROMISE
from .scan import matches
from .store import read_card

LOCAL_DIR = ".dev-charter"  # this clone's own settings; never committed
STRICT_FILE = "strict"
SIGNOFF_RE = re.compile(r"^- \d{4}-\d{2}-\d{2} ·.*$", re.MULTILINE)
STATE_RE = re.compile(r"^state:\s*(\S*)", re.MULTILINE)


def strict_until(config: Config) -> datetime | None:
    """Until when Strict mode was turned on for this clone, if it still is."""
    path = config.root / LOCAL_DIR / STRICT_FILE
    if not path.is_file():
        return None
    try:
        until = datetime.fromisoformat(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None
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


def _proposed(tool: str, given: dict, current: str) -> str:
    """The file's text after the edit Claude Code is about to make."""
    if tool == "Write":
        return str(given.get("content", ""))
    edits = given.get("edits") if tool == "MultiEdit" else [given]
    text = current
    for edit in edits or []:
        old, new = str(edit.get("old_string", "")), str(edit.get("new_string", ""))
        text = text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    return text


def _open_cards(config: Config) -> list:
    cards = []
    for path in sorted((config.charter_dir / CARD.folder).glob("*.md")):
        try:
            card = read_card(path)
        except CharterError:
            continue
        if card.state == "open":
            cards.append(card)
    return cards


def decide(payload: dict, cwd: Path) -> str | None:
    """Why this edit is refused, or None when it may go ahead. Anything Dev Charter does not manage goes ahead."""
    given = payload.get("tool_input") or {}
    raw = given.get("file_path") or given.get("notebook_path")
    if not raw:
        return None
    path = Path(raw)
    path = (path if path.is_absolute() else Path(payload.get("cwd") or cwd) / path).resolve()
    try:
        config = load(find_root(path.parent))
    except CharterError:
        return None
    if not is_strict(config):
        return None
    root = config.root.resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return None

    charter = f"{CHARTER_DIR}/"
    if relative.startswith((f"{charter}{FEATURE.folder}/", f"{charter}{PROMISE.folder}/")):
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        proposed = _proposed(str(payload.get("tool_name", "")), given, current)
        if set(SIGNOFF_RE.findall(proposed)) - set(SIGNOFF_RE.findall(current)):
            return ("Strict mode: only a person adds a sign-off. Tell the person what to check and let them sign "
                    "it off.")
        before, after = STATE_RE.search(current), STATE_RE.search(proposed)
        if current and (before.group(1) if before else "") != (after.group(1) if after else ""):
            return "Strict mode: only a person changes a feature's or a promise's state."
        return None
    if relative.startswith(charter) or relative.startswith(f"{LOCAL_DIR}/"):
        return None

    cards = _open_cards(config)
    if any(matches(relative, card.allowed) for card in cards if card.allowed):
        return None
    if not cards:
        return (f"Strict mode: {relative} can only change for an open task card. Make one with `dev-charter card "
                "new`, list the files it may change under '## Allowed paths', then try again.")
    allowed = "; ".join(f"{c.id}: {', '.join(c.allowed) or 'no paths listed'}" for c in cards)
    return (f"Strict mode: {relative} is not in the allowed paths of an open task card ({allowed}). If a check on "
            "the card cannot pass without it, follow the blocker test in `dev-charter guide build` and add it to the "
            "card's Allowed paths; otherwise park the idea with `dev-charter park`.")
