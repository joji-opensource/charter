# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Errors shown to people: plain English, with the file and line when there is one."""

import errno
from pathlib import Path

# The system refused a write: permissions, a read-only disk, or a coding agent's sandbox.
REFUSED = {errno.EPERM, errno.EACCES, errno.EROFS}


def refused_write(path: Path, reason: str, root: Path | None, by_an_agent: bool) -> str:
    """A write the system refused, said plainly, with the remedy that fits. An agent's sandbox lets it write only
    inside the folder it was started in, whichever folder it runs a command from, and never in .git (plan v0.2,
    probes C6 and C12)."""
    try:
        shown = path.resolve().relative_to(root.resolve()).as_posix() if root else str(path)
    except ValueError:
        shown = str(path)
    said = f"Dev Charter could not write {shown} ({reason})."
    if not by_an_agent:
        return said + " Make sure you may write there, then run the command again."
    if ".git" in path.parts:
        return said + (" A coding agent's sandbox keeps it out of .git (Codex's does): run the same command yourself "
                       "in a terminal.")
    return said + (" A coding agent's sandbox lets it write only inside the folder it was started in: start it in the "
                   f"product's root folder, {root or path.parent}, or run the same command yourself in a terminal.")


class CharterError(Exception):
    """A problem the person can fix; shown without a traceback."""


class FileProblem(CharterError):
    """A problem in one of the charter files, pointing at the line to fix."""

    def __init__(self, path: Path, line: int, message: str) -> None:
        super().__init__(message)
        self.path = path
        self.line = line
        self.message = message

    def where(self, root: Path | None = None) -> str:
        path = self.path
        if root is not None:
            try:
                path = self.path.relative_to(root)
            except ValueError:
                pass
        return f"{path}:{self.line}"

    def __str__(self) -> str:
        return f"{self.where()}: {self.message}"
