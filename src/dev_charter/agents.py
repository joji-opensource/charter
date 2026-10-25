# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The managed block in AGENTS.md that tells coding agents how work is done in this repository."""

from __future__ import annotations

import re
from pathlib import Path

from . import __version__
from .errors import CharterError
from .store import template

AGENTS_FILE = "AGENTS.md"
END = "<!-- dev-charter:end -->"
BLOCK_RE = re.compile(r"<!-- dev-charter:start v(?P<version>\S+) -->.*?<!-- dev-charter:end -->", re.DOTALL)


def render_block(version: str = __version__) -> str:
    return f"<!-- dev-charter:start v{version} -->\n{template('agents_block.md').rstrip()}\n{END}"


def block_version(root: Path) -> str | None:
    """The Dev Charter version that wrote the block, or None when there is no block."""
    path = root / AGENTS_FILE
    if not path.is_file():
        return None
    match = BLOCK_RE.search(path.read_text(encoding="utf-8"))
    return match.group("version") if match else None


def write_block(root: Path) -> str:
    """Create or refresh the block, leaving every line outside it untouched. Returns created, updated or unchanged."""
    path = root / AGENTS_FILE
    block = render_block()
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
