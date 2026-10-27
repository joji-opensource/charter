# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The managed block in AGENTS.md that tells coding agents how work is done in this repository, and the short pointer
to it in each listed folder where Codex would not find it."""

from __future__ import annotations

import os
import re
from pathlib import Path

from packaging.version import InvalidVersion, Version

from . import __version__, git
from .config import Config
from .errors import CharterError
from .store import template

AGENTS_FILE = "AGENTS.md"
OVERRIDE_FILE = "AGENTS.override.md"  # Codex reads this instead of AGENTS.md in the same folder
CODEX_LIMIT = 32 * 1024  # the bytes of instructions Codex reads, by default
END = "<!-- dev-charter:end -->"
BLOCK_RE = re.compile(r"<!-- dev-charter:start v(?P<version>\S+) -->.*?<!-- dev-charter:end -->", re.DOTALL)

# What the block is, compared with what the installed Dev Charter would write.
MISSING, CURRENT, OLDER, EDITED, NEWER = "missing", "current", "older", "edited", "newer"


def render_block(version: str | None = None, body: str | None = None) -> str:
    """The block, with the rules (or, for a pointer, the given body) between its markers."""
    text = template("agents_block.md") if body is None else body
    return f"<!-- dev-charter:start v{version or __version__} -->\n{text.rstrip()}\n{END}"


def pointer_body(product: str, to_root: str) -> str:
    return template("agents_child_block.md").replace("{{product}}", product).replace("{{path}}", to_root)


def pointer_folders(config: Config) -> list[tuple[Path, str]]:
    """The listed folders where Codex would not find the root's AGENTS.md, each with its path to the root. Codex reads
    AGENTS.md from the top of the git repository it starts in down to its folder, or, outside git, only its folder;
    so a folder that is the top of its own repository, or is in none, needs a pointer (plan v0.2, probe C7)."""
    found = []
    root = config.root.resolve()
    for repo in config.repos:
        folder = repo.path.resolve()
        if folder == root:
            continue
        top = git.toplevel(folder)
        if top is None or top.resolve() == folder:
            found.append((folder, Path(os.path.relpath(root, folder)).as_posix()))
    return found


def _parse(version: str) -> Version | None:
    try:
        return Version(version)
    except InvalidVersion:
        return None


def block_state(root: Path, version: str | None = None, body: str | None = None) -> tuple[str, str | None]:
    """How the block in the folder's AGENTS.md compares with what this Dev Charter would write, and the version that
    wrote it.

    Older: written by an earlier Dev Charter, and its text differs. Edited: same version, text changed by hand.
    Newer: written by a later Dev Charter, so this one must not touch it (that is what stops teammates on different
    releases rewriting it back and forth).
    """
    version = version or __version__
    path = root / AGENTS_FILE
    match = BLOCK_RE.search(path.read_text(encoding="utf-8")) if path.is_file() else None
    if match is None:
        return MISSING, None
    written, installed = match.group("version"), _parse(version)
    written_as = _parse(written)
    if written_as is not None and installed is not None and written_as > installed:
        return NEWER, written
    if match.group(0) == render_block(version, body):
        return CURRENT, written
    if written_as is not None and installed is not None and written_as == installed:
        return EDITED, written
    return OLDER, written


def write_block(root: Path, version: str | None = None, body: str | None = None) -> str:
    """Create or refresh the block, leaving every line outside it untouched. Returns created, updated, unchanged, or
    newer (left alone because a later Dev Charter wrote it)."""
    state, _ = block_state(root, version, body)
    if state == NEWER:
        return NEWER
    path = root / AGENTS_FILE
    block = render_block(version, body)
    if not path.exists():
        path.write_text(block + "\n", encoding="utf-8")
        return "created"
    text = path.read_text(encoding="utf-8")
    matches = list(BLOCK_RE.finditer(text))
    if len(matches) > 1:
        raise CharterError(f"{AGENTS_FILE} has {len(matches)} Dev Charter blocks; delete all but one and run again.")
    if matches:
        new_text = text[: matches[0].start()] + block + text[matches[0].end():]
    elif not text.strip():
        new_text = block + "\n"
    else:
        new_text = (text if text.endswith("\n") else text + "\n") + "\n" + block + "\n"
    if new_text == text:
        return "unchanged"
    path.write_text(new_text, encoding="utf-8")
    return "updated"


def write_pointers(config: Config) -> list[str]:
    """Write or refresh the pointer in each folder that needs one; one plain line for each that changed."""
    notes = []
    for folder, to_root in pointer_folders(config):
        outcome = write_block(folder, body=pointer_body(config.product, to_root))
        shown = Path(os.path.relpath(folder, config.root)).as_posix()
        if outcome == NEWER:
            notes.append(f"{shown}/{AGENTS_FILE}: left as it is; a newer Dev Charter wrote its pointer.")
        elif outcome != "unchanged":
            notes.append(f"{shown}/{AGENTS_FILE}: {outcome} the pointer to {config.product}'s rules.")
    return notes
