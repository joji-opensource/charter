# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Reading a coding agent's edit from its hook's payload, whichever agent made it: Claude Code's edit tools, and
Codex's patches (`apply_patch`, also when one arrives inside a shell command)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CLAUDE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
BEGIN, END, END_OF_FILE = "*** Begin Patch", "*** End Patch", "*** End of File"
FILE_RE = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+)$")
MOVE_RE = re.compile(r"^\*\*\* Move to: (.+)$")


class UnreadableEdit(ValueError):
    """An edit Dev Charter cannot read; the message says why, in plain words."""


@dataclass(frozen=True)
class Hunk:
    anchor: str  # the text after @@, which places the change; may be empty
    old: tuple[str, ...]  # the lines around the change and the lines it removes, in order
    new: tuple[str, ...]  # the lines around the change and the lines it adds, in order


@dataclass(frozen=True)
class Change:
    op: str  # add, update or delete (a Codex patch), or edit (one of Claude Code's tools)
    path: Path  # absolute
    to: Path | None = None  # where an update moves the file
    added: tuple[str, ...] = ()  # the lines of a file a patch adds
    hunks: tuple[Hunk, ...] = ()  # what a patch changes in a file


def _absolute(raw: str, base: Path) -> Path:
    path = Path(raw.strip())
    return path if path.is_absolute() else base / path


def shell_command(payload: dict) -> str | None:
    """The command of a shell tool call (both agents call the tool Bash), or None for any other tool."""
    if payload.get("tool_name") != "Bash":
        return None
    given = payload.get("tool_input")
    command = given.get("command") if isinstance(given, dict) else given
    if isinstance(command, list):
        return " ".join(str(part) for part in command)
    return command if isinstance(command, str) else None


def changes(payload: dict, cwd: Path) -> list[Change]:
    """The files an edit changes, or [] when the tool call is not an edit. Raises UnreadableEdit."""
    tool = str(payload.get("tool_name", ""))
    given = payload.get("tool_input")
    base = Path(payload.get("cwd") or cwd)
    if tool in CLAUDE_TOOLS:
        raw = given.get("file_path") or given.get("notebook_path") if isinstance(given, dict) else None
        if not raw:
            raise UnreadableEdit(f"the {tool} names no file")
        return [Change("edit", _absolute(str(raw), base))]
    if tool == "apply_patch":
        text = given.get("command") if isinstance(given, dict) else given
        if not isinstance(text, str):
            raise UnreadableEdit("the patch is not text")
        return parse_patch(text, base)
    command = shell_command(payload)
    if command is not None and BEGIN in command:
        return parse_patch(command, base)
    return []


def parse_patch(text: str, base: Path) -> list[Change]:
    """A Codex patch: `*** Begin Patch`, then for each file `*** Add File:` with `+` lines, `*** Delete File:`, or
    `*** Update File:` (optionally `*** Move to:`) with hunks of ` `, `-` and `+` lines, each hunk opened by `@@`
    (the first may not be), then `*** End Patch`."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == BEGIN), None)
    if start is None:
        raise UnreadableEdit(f"the patch has no '{BEGIN}' line")
    found: list[Change] = []
    i = start + 1
    while i < len(lines) and lines[i].strip() != END:
        match = FILE_RE.match(lines[i])
        if not match:
            raise UnreadableEdit(f"the patch line '{lines[i][:60]}' is not one Dev Charter knows")
        op, path = match.group(1).lower(), _absolute(match.group(2), base)
        i += 1
        if op == "add":
            added = []
            while i < len(lines) and lines[i].startswith("+"):
                added.append(lines[i][1:])
                i += 1
            found.append(Change("add", path, added=tuple(added)))
        elif op == "delete":
            found.append(Change("delete", path))
        else:
            to = None
            if i < len(lines) and (move := MOVE_RE.match(lines[i])):
                to, i = _absolute(move.group(1), base), i + 1
            hunks, i = _hunks(lines, i)
            found.append(Change("update", path, to=to, hunks=hunks))
    if i >= len(lines):
        raise UnreadableEdit(f"the patch has no '{END}' line")
    if not found:
        raise UnreadableEdit("the patch changes no file")
    return found


def _hunks(lines: list[str], i: int) -> tuple[tuple[Hunk, ...], int]:
    hunks: list[tuple[str, list[str], list[str]]] = []
    while i < len(lines):
        line = lines[i]
        if line == END_OF_FILE:
            i += 1
            continue
        if line.startswith("*** "):
            break
        if line.startswith("@@"):
            hunks.append((line[2:].strip(), [], []))
            i += 1
            continue
        if not hunks:
            hunks.append(("", [], []))
        _, old, new = hunks[-1]
        mark, rest = (line[0], line[1:]) if line else (" ", "")
        if mark not in " -+":
            raise UnreadableEdit(f"the patch line '{line[:60]}' is not one Dev Charter knows")
        if mark != "+":
            old.append(rest)
        if mark != "-":
            new.append(rest)
        i += 1
    return tuple(Hunk(anchor, tuple(old), tuple(new)) for anchor, old, new in hunks), i


def text_after(change: Change, payload: dict, current: str) -> str | None:
    """The file's text after the change, or None when it deletes the file. Raises UnreadableEdit when a patch cannot
    be placed in the file exactly."""
    if change.op == "delete":
        return None
    if change.op == "add":
        return "".join(f"{line}\n" for line in change.added)
    if change.op == "edit":
        return proposed(str(payload.get("tool_name", "")), payload.get("tool_input") or {}, current)
    return apply_hunks(current, change.hunks)


def proposed(tool: str, given: dict, current: str) -> str:
    """The file's text after the edit one of Claude Code's tools is about to make."""
    if tool == "Write":
        return str(given.get("content", ""))
    edits = given.get("edits") if tool == "MultiEdit" else [given]
    text = current
    for edit in edits or []:
        old, new = str(edit.get("old_string", "")), str(edit.get("new_string", ""))
        text = text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    return text


def apply_hunks(text: str, hunks: tuple[Hunk, ...]) -> str:
    """Apply a patch's hunks only where each fits exactly one place, after the one before it. Where Codex itself
    would bend the rules (spaces at the ends of lines, a place found twice), Dev Charter does not guess."""
    lines = text.splitlines()
    position = 0
    for hunk in hunks:
        start = position
        if hunk.anchor:
            places = [k for k in range(position, len(lines)) if lines[k].strip() == hunk.anchor]
            if len(places) != 1:
                raise UnreadableEdit(f"the place '@@ {hunk.anchor}' is in the file {len(places)} times, not once")
            start = places[0]
        if not hunk.old:
            raise UnreadableEdit("a change with no lines around it cannot be placed")
        size = len(hunk.old)
        places = [k for k in range(start, len(lines) - size + 1) if tuple(lines[k:k + size]) == hunk.old]
        if len(places) != 1:
            raise UnreadableEdit(f"a change fits {len(places)} places in the file, not one")
        lines[places[0]:places[0] + size] = hunk.new
        position = places[0] + len(hunk.new)
    return "".join(f"{line}\n" for line in lines)
