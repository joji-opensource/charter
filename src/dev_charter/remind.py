# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Telling Claude Code, right after it edits a code file, when that file does not say which feature it serves,
and keeping the words in tags in step with the charter on request."""

from __future__ import annotations

import re
from pathlib import Path

from .config import Config, find_root, load
from .errors import CharterError
from .scan import TAG_REF_RE, is_code, read_tags
from .store import Project, load_project, open_cards

HASH = {".py", ".pyi", ".rb", ".sh", ".r", ".ex", ".exs", ".pl", ".yml", ".yaml", ".toml"}
DASHES = {".sql", ".lua"}
MAX_LINE = 100


def comment_for(path: Path) -> str:
    suffix = path.suffix.lower()
    return "#" if suffix in HASH else "--" if suffix in DASHES else "//"


def _words(entries: dict, ref: str) -> str:
    """The charter's wording for a feature (its title) or a check (its text)."""
    entry_id, _, letter = ref.partition(".")
    entry = entries.get(entry_id)
    if entry is None:
        return ""
    if letter:
        return next((c.text for c in entry.criteria if c.letter == letter), "")
    return entry.title


def note(payload: dict, cwd: Path) -> str | None:
    """What to tell Claude after an edit, or None when the file is tagged or not a code file Dev Charter tracks."""
    raw = (payload.get("tool_input") or {}).get("file_path")
    if not raw:
        return None
    path = Path(raw)
    path = (path if path.is_absolute() else Path(payload.get("cwd") or cwd) / path).resolve()
    try:
        config = load(find_root(path.parent))
    except CharterError:
        return None
    repo, relative = None, ""
    for candidate in config.repos:
        try:
            relative = path.relative_to(candidate.path.resolve()).as_posix()
        except ValueError:
            continue
        repo = candidate
        break
    if repo is None or not is_code(relative, repo):
        return None
    try:
        if read_tags(path.read_text(encoding="utf-8")):
            return None
    except (OSError, UnicodeDecodeError):
        return None

    c = comment_for(path)
    cards = [card for card in open_cards(config) if card.serves]
    if not cards:
        return (f"{relative} does not say which feature it serves. Add `{c} serves: F-nnn — <what it is>` near the "
                f"top for the feature this change is for, or `{c} serves: foundation` if every feature relies on it. "
                "If no feature fits, stop and ask: work that serves no feature is parked, not built.")
    entries = {e.id: e for e in load_project(config).entries}
    card = cards[0]
    features = list(dict.fromkeys(ref.split(".")[0] for ref in card.serves))
    top = f"{c} serves: {', '.join(features)}"
    if len(features) == 1 and _words(entries, features[0]):
        top += f" — {_words(entries, features[0])}"
    message = (f"{relative} does not say which feature it serves. You are working on {card.id} ({card.title}), which "
               f"serves {', '.join(card.serves)}: add `{top}` near the top of the file")
    checks = [ref for ref in card.serves if "." in ref]
    if checks:
        example = f"{c} serves: {checks[0]} — {_words(entries, checks[0])}".rstrip(" —")
        message += f", and above the code for each check it delivers, a line such as `{example}`"
    return message + "."


def refresh(config: Config, project: Project, files) -> list[tuple[Path, int, str]]:
    """Rewrite the words of every single-item tag to the charter's wording. Returns (file, line, new text)."""
    entries = {e.id: e for e in project.entries}
    changed = []
    for code in files:
        targets = {tag.line: tag for tag in code.tags if len(tag.refs) == 1 and _words(entries, tag.refs[0])}
        if not targets:
            continue
        lines = code.absolute.read_text(encoding="utf-8").splitlines(keepends=True)
        touched = False
        for number, tag in targets.items():
            line = lines[number - 1]
            ref = tag.refs[0]
            match = re.search(rf"serves:\s*{re.escape(ref)}(?![A-Za-z0-9])", line, re.IGNORECASE)
            if not match or not TAG_REF_RE.search(line):
                continue
            ending = "\n" if line.endswith("\n") else ""
            closer = re.search(r"\s*(\*/|-->)\s*$", line.rstrip("\n"))
            head = line[: match.end()]
            words = _words(entries, ref)
            room = MAX_LINE - len(head) - 3 - (len(closer.group(0)) if closer else 0)
            if len(words) > room > 10:
                words = words[: room - 1].rstrip() + "…"
            new_line = f"{head} — {words}" + (closer.group(0) if closer else "") + ending
            if new_line != line:
                lines[number - 1] = new_line
                changed.append((code.absolute, number, new_line.strip()))
                touched = True
        if touched:
            code.absolute.write_text("".join(lines), encoding="utf-8")
    return changed
