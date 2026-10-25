# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Errors shown to people: plain English, with the file and line when there is one."""

from pathlib import Path


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
