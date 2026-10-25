# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The plain-English summary of what a pull request changes in the product, and the checks it must pass."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import check, git
from .config import CHARTER_DIR, Config
from .errors import FileProblem
from .model import DECISION, FEATURE, PROMISE, Entry, Kind
from .report import take_snapshot
from .store import Project, read_entry
from .trace import Trace


@dataclass
class Summary:
    markdown: str
    problems: list[str] = field(default_factory=list)


def _at(config: Config, ref: str, kind: Kind) -> dict[str, tuple[str, str]]:
    """Each ID of this kind at `ref`: its file name and text."""
    root = config.root
    prefix = git.prefix(root)
    paths = git.files_at(root, ref, f"{CHARTER_DIR}/{kind.folder}")
    texts = git.read_many(root, [f"{ref}:{p}" for p in paths])
    found = {}
    for path in paths:
        name = Path(path).name
        item_id = name.split("-", 2)
        if len(item_id) < 2 or not name.endswith(".md"):
            continue
        found[f"{item_id[0]}-{item_id[1].split('.')[0]}"] = (path.removeprefix(prefix), texts.get(f"{ref}:{path}"))
    return found


def _entry_from(text: str | None, path: str, kind: Kind) -> Entry | None:
    if not text:
        return None
    try:
        return read_entry(Path(path), kind, text)
    except FileProblem:
        return None


def _what_changed(before: Entry, after: Entry) -> list[str]:
    changes = []
    if before.state != after.state:
        changes.append(f"state {before.state} → {after.state}")
    if before.story != after.story:
        changes.append("story reworded")
    before_checks = {c.letter: c.text for c in before.criteria}
    after_checks = {c.letter: c.text for c in after.criteria}
    added = sorted(set(after_checks) - set(before_checks))
    removed = sorted(set(before_checks) - set(after_checks))
    reworded = sorted(k for k in set(before_checks) & set(after_checks) if before_checks[k] != after_checks[k])
    if added:
        changes.append(f"new checks {', '.join(added)}")
    if removed:
        changes.append(f"checks removed {', '.join(removed)}")
    if reworded:
        changes.append(f"checks reworded {', '.join(reworded)}")
    old_signoffs = {(s.what, s.person, s.note) for s in before.signoffs}
    for s in after.signoffs:
        if (s.what, s.person, s.note) not in old_signoffs:
            changes.append(f"signed off ({s.what}) by {s.person}: {s.note}")
    return changes


def summarise(config: Config, project: Project, trace: Trace, base: str) -> Summary:
    root = config.root
    snap = take_snapshot(project, trace)
    lines = [f"## What this pull request changes in {config.product}", ""]
    problems: list[str] = []

    for kind in (FEATURE, PROMISE, DECISION):
        on_base = _at(config, base, kind)
        here = {item.id: item for item in (project.features if kind is FEATURE else project.promises
                                           if kind is PROMISE else project.decisions)}
        for item_id, item in here.items():
            if item_id in on_base and Path(on_base[item_id][0]).name != item.path.name:
                problems.append(f"{item_id} is already used on {base} by {Path(on_base[item_id][0]).name}. Run "
                                f"`dev-charter renumber {item_id}` on this branch, then push again.")
        added = sorted(set(here) - set(on_base))
        removed = sorted(set(on_base) - set(here))
        if kind is DECISION:
            for item_id in added:
                lines.append(f"- **New decision {item_id}:** {here[item_id].title}. {here[item_id].decision}")
            continue
        noun = kind.name
        for item_id in added:
            entry = here[item_id]
            lines.append(f"- **New {noun} {item_id}:** {entry.title} ({entry.state}; {snap.of(entry).checks})")
        for item_id in removed:
            lines.append(f"- **{noun.capitalize()} {item_id} removed** from the charter.")
        for item_id in sorted(set(here) & set(on_base)):
            before = _entry_from(on_base[item_id][1], on_base[item_id][0], kind)
            after = here[item_id]
            if before is None:
                continue
            changes = _what_changed(before, after)
            if changes:
                lines.append(f"- **{item_id} {after.title}:** {'; '.join(changes)}. Now {snap.of(after).name}, "
                             f"{snap.of(after).checks}.")
    if len(lines) == 2:
        lines.append("- No features, promises or decisions change.")

    changes = {}
    for repo in config.repos:
        out = git.run(repo.path, "diff", "--name-status", "--relative", "--diff-filter=ACMR", f"{base}...HEAD") or ""
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                changes[repo.path / parts[-1]] = "new" if parts[0][0] in "AC" else "changed"
    touched = [f for f in trace.files if f.absolute in changes]
    if touched:
        serves = sorted({i for f in touched for i in f.serves})
        unexplained = [f.path for f in touched if f.kind == "Unexplained"]
        lines += ["", f"**Code:** {len(touched)} file(s) changed"
                  + (f", serving {', '.join(serves)}" if serves else "")
                  + (f"; {len(unexplained)} serve no feature: {', '.join(unexplained)}" if unexplained else "") + "."]

    findings = check.run(project, trace, changes, staged=True)
    problems += [f"{f.message} ({f.where(root)})" if f.path else f.message
                 for f in findings if f.level == check.PROBLEM]
    if problems:
        lines += ["", "### Must be fixed before merging", ""] + [f"- {p}" for p in problems]
    else:
        lines += ["", "Nothing to fix: the charter and its trace are in order."]
    return Summary("\n".join(lines) + "\n", problems)
