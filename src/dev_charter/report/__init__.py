# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The generated views of a charter: LEDGER.xlsx and status.html, built from one snapshot."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .. import git
from ..errors import CharterError
from ..model import Entry
from ..status import ORDER, Status, status
from ..store import Project
from ..trace import Trace

LEDGER_FILE = "LEDGER.xlsx"
STATUS_FILE = "status.html"
GENERATED = (LEDGER_FILE, STATUS_FILE)
NOT_STARTED = ("Idea", "Parked", "Retired")


@dataclass
class Snapshot:
    project: Project
    trace: Trace
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
            source = f"commit {self.commit[:7]}" + (" with uncommitted changes" if self.uncommitted else "")
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

    def built_in(self, entry: Entry) -> str:
        """The repositories and files that serve an entry, one line per repository."""
        by_repo: dict[str, list[str]] = {}
        for code in self.trace.built_in(entry.id):
            by_repo.setdefault(code.repo.name, []).append(code.path)
        return "\n".join(f"{name}: {' · '.join(sorted(paths))}" for name, paths in by_repo.items())

    def proven_by(self, entry: Entry) -> str:
        tests = self.trace.tests_for(entry.id)
        lines = []
        if tests:
            passed = sum(1 for t in tests if t.outcome == "passed")
            failed = sum(1 for t in tests if t.outcome == "failed")
            counts = f"{passed} passed" + (f", {failed} failed" if failed else "")
            newest = max(f.written for f in self.trace.results.files if f.path in {t.source for t in tests})
            lines.append(f"{len(tests)} automated checks ({counts}) · results of {newest:%d %b %H:%M}")
        if entry.signoffs:
            people = sorted({s.person for s in entry.signoffs})
            lines.append(f"{len(entry.signoffs)} sign-off{'s' if len(entry.signoffs) > 1 else ''} by "
                         f"{', '.join(people)}")
        return "\n".join(lines)


def take_snapshot(project: Project, trace: Trace | None = None) -> Snapshot:
    root = project.config.root
    trace = trace or Trace()
    statuses = {entry.id: status(entry, trace.outcomes, trace.tagged) for entry in project.entries}
    snap = Snapshot(project, trace, statuses, datetime.now())
    snap.commit = git.head(root)
    if snap.commit:
        # Untracked files are listed one by one; otherwise git folds a new folder into a single line.
        snap.uncommitted = bool((git.run(root, "status", "--porcelain", "--untracked-files=all", "--", ".")
                                 or "").strip())
    pending = git.run(root, "status", "--porcelain", "--untracked-files=all", "--", "charter") or ""
    changed = (git.run(root, "log", "--since=7.days", "--name-only", "--format=", "--", "charter") or "") + pending
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
