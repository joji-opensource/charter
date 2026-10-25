# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The generated views of a charter: LEDGER.xlsx and status.html, built from one snapshot."""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..errors import CharterError
from ..model import Entry
from ..status import ORDER, Status, status
from ..store import Project

LEDGER_FILE = "LEDGER.xlsx"
STATUS_FILE = "status.html"
GENERATED = (LEDGER_FILE, STATUS_FILE)
NOT_STARTED = ("Idea", "Parked", "Retired")


@dataclass
class Snapshot:
    project: Project
    statuses: dict[str, Status]
    generated: datetime
    commit: str | None = None
    uncommitted: bool = False
    recent: list[str] = field(default_factory=list)  # IDs whose files changed in the last 7 days

    def of(self, entry: Entry) -> Status:
        return self.statuses[entry.id]

    @property
    def provenance(self) -> str:
        when = self.generated.strftime("%d %b %Y %H:%M")
        if self.commit is None:
            source = "files that are not in git"
        else:
            source = f"commit {self.commit}" + (" with uncommitted changes" if self.uncommitted else "")
        return f"Generated {when} from {source}."

    def counts(self, entries: list[Entry]) -> dict[str, int]:
        counts = dict.fromkeys(ORDER, 0)
        for entry in entries:
            counts[self.of(entry).name] += 1
        return counts

    def proven_share(self) -> tuple[int, int]:
        """Features proven or live, out of features that are agreed or further along."""
        active = [f for f in self.project.features if self.of(f).name not in NOT_STARTED]
        done = [f for f in active if self.of(f).name in ("Proven", "Live")]
        return len(done), len(active)


def _git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def take_snapshot(
    project: Project,
    outcomes: Mapping[str, list[str]] | None = None,
    tagged: Set[str] = frozenset(),
) -> Snapshot:
    root = project.config.root
    statuses = {entry.id: status(entry, outcomes, tagged) for entry in project.entries}
    snap = Snapshot(project, statuses, datetime.now())
    # Untracked files are listed one by one; otherwise git folds a new folder into a single line.
    pending = _git(root, "status", "--porcelain", "--untracked-files=all", "--", "charter") or ""
    head = _git(root, "rev-parse", "--short", "HEAD")
    if head:
        snap.commit = head.strip()
        snap.uncommitted = bool(pending.strip())
    changed = (_git(root, "log", "--since=7.days", "--name-only", "--format=", "--", "charter") or "") + pending
    names = {Path(line.strip().split()[-1]).name for line in changed.splitlines() if line.strip()}
    snap.recent = sorted(e.id for e in project.entries if e.path.name in names)
    return snap


def write_atomically(path: Path, write: Callable[[Path], None]) -> None:
    """Write next to the target and swap it in, so a reader never sees half a file."""
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}-", suffix=path.suffix)
    os.close(handle)
    temp_path = Path(temp)
    try:
        write(temp_path)
        os.replace(temp_path, path)
    except PermissionError as exc:
        raise CharterError(f"{path.name} could not be replaced; close it in any program that has it open "
                           "and run again.") from exc
    finally:
        temp_path.unlink(missing_ok=True)


def write_reports(snap: Snapshot) -> list[Path]:
    from .html import write_html
    from .xlsx import write_xlsx

    root = snap.project.config.root
    ledger, page = root / LEDGER_FILE, root / STATUS_FILE
    write_atomically(ledger, lambda p: write_xlsx(snap, p))
    write_atomically(page, lambda p: write_html(snap, p))
    return [ledger, page]
