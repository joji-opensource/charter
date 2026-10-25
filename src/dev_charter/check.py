# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""`dev-charter check`: problems that must be fixed, and warnings worth a look, each with its file and line."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .agents import AGENTS_FILE, block_version
from .store import PLACEHOLDER_RE, Project

PROBLEM, WARNING = "problem", "warning"
MAX_WORDS = 250


@dataclass(frozen=True)
class Finding:
    level: str
    message: str
    path: Path | None = None
    line: int | None = None

    def where(self, root: Path) -> str:
        if self.path is None:
            return ""
        try:
            shown = self.path.relative_to(root).as_posix()
        except ValueError:
            shown = str(self.path)
        return f"{shown}:{self.line}" if self.line else shown


def run(project: Project) -> list[Finding]:
    config = project.config
    findings = [Finding(PROBLEM, p.message, p.path, p.line) for p in project.problems]

    files_by_id: dict[str, list[Path]] = {}
    for item in [*project.entries, *project.decisions, *project.cards]:
        files_by_id.setdefault(item.id, []).append(item.path)
    for item_id, paths in files_by_id.items():
        for path in paths[1:]:
            findings.append(Finding(PROBLEM, f"{item_id} is also used by {paths[0].name}; give one of them a new ID "
                                    f"with `dev-charter <kind> new`, then move its text across.", path, 2))

    entries = {e.id: e for e in project.entries}
    decisions = {d.id for d in project.decisions}
    for entry in project.entries:
        for ref in entry.decisions:
            if ref not in decisions:
                findings.append(Finding(PROBLEM, f"{entry.id} refers to decision {ref}, which does not exist.",
                                        entry.path, 2))
    for decision in project.decisions:
        for ref in decision.features:
            if ref.split(".")[0] not in entries:
                findings.append(Finding(PROBLEM, f"{decision.id} refers to {ref}, which does not exist.",
                                        decision.path, 2))
    for card in project.cards:
        if card.state == "open" and PLACEHOLDER_RE.search(card.goal):
            findings.append(Finding(WARNING, f"{card.id} still has template text in its Goal.", card.path, None))
        if not card.serves:
            findings.append(Finding(WARNING, f"{card.id} does not say which checks it serves (serves: [F-014.a]).",
                                    card.path, 2))
        for ref in card.serves:
            entry_id, _, letter = ref.partition(".")
            entry = entries.get(entry_id)
            if entry is None:
                findings.append(Finding(PROBLEM, f"{card.id} serves {ref}, but {entry_id} does not exist.",
                                        card.path, 2))
            elif letter and letter not in {c.letter for c in entry.criteria}:
                findings.append(Finding(PROBLEM, f"{card.id} serves {ref}, but {entry_id} has no check '{letter}.'.",
                                        card.path, 2))

    internal = [w for w in config.internal_words if w.strip()]
    for entry in project.entries:
        if entry.state != "idea":
            for line, where in entry.placeholders:
                findings.append(Finding(WARNING, f"{entry.id} still has template text in '{where}'.", entry.path,
                                        line))
        if entry.words > MAX_WORDS:
            findings.append(Finding(WARNING, f"{entry.id} is {entry.words} words; over {MAX_WORDS} it is usually two "
                                    f"{entry.kind.name}s.", entry.path, 1))
        if config.areas and entry.kind.name == "feature" and entry.area not in config.areas:
            findings.append(Finding(WARNING, f"{entry.id}'s area '{entry.area}' is not one of the areas in "
                                    "charter.toml.", entry.path, 2))
        texts = [entry.title, *entry.story.values(), *(c.text for c in entry.criteria)]
        findings += _internal_words(entry.id, entry.path, texts, internal)
    for decision in project.decisions:
        texts = [decision.title, decision.decided_by, decision.decision, decision.instead_of, decision.because]
        if any(PLACEHOLDER_RE.search(t) for t in texts):
            findings.append(Finding(WARNING, f"{decision.id} still has template text.", decision.path, 1))
        findings += _internal_words(decision.id, decision.path, texts, internal)

    written_by = block_version(config.root)
    if written_by is None:
        findings.append(Finding(WARNING, f"{AGENTS_FILE} has no Dev Charter block, so coding agents do not know the "
                                "rules. Run `dev-charter sync`.", config.root / AGENTS_FILE))
    elif written_by != __version__:
        findings.append(Finding(WARNING, f"The block in {AGENTS_FILE} was written by Dev Charter {written_by}; "
                                f"{__version__} is installed. Run `dev-charter sync`.", config.root / AGENTS_FILE))
    return sorted(findings, key=lambda f: (f.level != PROBLEM, str(f.path or ""), f.line or 0))


def _internal_words(item_id: str, path: Path, texts: list[str], words: list[str]) -> list[Finding]:
    found = Counter()
    for word in words:
        pattern = re.compile(rf"(?<!\w){re.escape(word)}(?!\w)", re.IGNORECASE)
        for text in texts:
            found[word] += len(pattern.findall(text or ""))
    return [Finding(WARNING, f"{item_id} uses the in-house word '{word}'; say it in plain English.", path, None)
            for word, count in found.items() if count]
