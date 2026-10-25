# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Moving an item to a new ID when two branches gave out the same one, and every reference with it."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import git
from .config import Config
from .errors import CharterError
from .model import CARD, DECISION, FEATURE, PROMISE, Kind
from .results import PARAMETERS_RE
from .scan import is_test
from .store import Project, next_id, used_ids
from .trace import Trace


@dataclass
class Renumbered:
    old: str
    new: str
    path: Path
    changed: list[tuple[Path, int, str]] = field(default_factory=list)
    listed: list[tuple[Path, int, str]] = field(default_factory=list)


def kind_of(item_id: str) -> Kind:
    for kind in (DECISION, CARD, FEATURE, PROMISE):  # the longer prefixes first
        if re.fullmatch(rf"{kind.prefix}-\d{{3,}}", item_id):
            return kind
    raise CharterError(f"'{item_id}' is not an ID like F-014, P-002, DEC-001 or CARD-007.")


def _whole(item_id: str) -> re.Pattern:
    """The ID as charter files and `serves:` lines write it, never inside a longer one."""
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(item_id)}(?![0-9])")


def _test_form(item_id: str) -> re.Pattern:
    """The ID in any form a test name gives it: F-017.a, F017_a, TestF017A."""
    prefix, digits = item_id.split("-", 1)
    return re.compile(rf"(?<![A-Z0-9])({prefix})(-?){digits}(?![0-9])")


def _rewrite(path: Path, pattern: re.Pattern, replacement, only_lines: re.Pattern | None,
             changed: list[tuple[Path, int, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    touched = False
    for number, line in enumerate(lines, start=1):
        if only_lines is not None and not only_lines.search(line):
            continue
        new_line = pattern.sub(replacement, line)
        if new_line != line:
            lines[number - 1] = new_line
            changed.append((path, number, new_line.strip()))
            touched = True
    if touched:
        path.write_text("".join(lines), encoding="utf-8")


def renumber(config: Config, project: Project, trace: Trace, old: str, new: str | None = None) -> Renumbered:
    kind = kind_of(old)
    items = {item.id: item for item in [*project.entries, *project.decisions, *project.cards]}
    if old not in items:
        raise CharterError(f"There is no {old} in charter/.")
    if new is None:
        new = next_id(config, kind)
    elif kind_of(new) is not kind:
        raise CharterError(f"{new} is not the same kind of ID as {old}.")
    elif int(new.split("-")[1]) in used_ids(config, kind):
        raise CharterError(f"{new} has already been used on some branch, and IDs are never reused. Leave out --to "
                           "to take the next free one.")

    result = Renumbered(old, new, items[old].path)
    whole = _whole(old)
    for path in sorted(config.charter_dir.rglob("*.md")):
        _rewrite(path, whole, new, None, result.changed)

    if kind in (FEATURE, PROMISE):
        serves_line = re.compile(r"serves:", re.IGNORECASE)
        for code in trace.files:
            _rewrite(code.absolute, whole, new, serves_line, result.changed)

        form = _test_form(old)
        new_digits = new.split("-", 1)[1]

        def renamed(name: str) -> str:
            return form.sub(lambda m: f"{m.group(1)}{m.group(2)}{new_digits}", name)

        names = {PARAMETERS_RE.sub("", case.name) for case in trace.results.cases
                 if any(i == old or i.startswith(old + ".") for i in case.ids)}
        test_files = [repo.path / rel for repo in config.repos
                      for rel in _repo_files(repo.path) if is_test(rel, repo)]
        for path in test_files:
            try:
                path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for name in sorted(names, key=len, reverse=True):
                exact = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")
                _rewrite(path, exact, renamed(name), None, result.changed)
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if form.search(line):
                    result.listed.append((path, number, line.strip()))

    target = result.path.with_name(result.path.name.replace(old, new, 1))
    result.path.rename(target)
    result.path = target
    return result


def _repo_files(folder: Path) -> list[str]:
    listed = git.files(folder)
    if listed is not None:
        return listed[0]
    return [p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()]
