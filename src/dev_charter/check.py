# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""`dev-charter check`: problems that must be fixed, and warnings worth a look, each with its file and line."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from . import git, hooks
from .agents import AGENTS_FILE, block_version, minor
from .store import LEGACY_HANDOFF_FILE, PLACEHOLDER_RE, Project
from .trace import Trace

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


def run(project: Project, trace: Trace | None = None, changes: dict[Path, str] | None = None,
        staged: bool = False) -> list[Finding]:
    """All the checks. `changes` maps changed code files to 'new' or 'changed'; `staged` limits the trace checks to
    what is about to be committed."""
    config = project.config
    findings = [Finding(PROBLEM, p.message, p.path, p.line) for p in project.problems]
    if trace is not None:
        findings += _trace_findings(project, trace, changes or {}, staged)

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

    if staged:
        return _ordered(findings)
    written_by = block_version(config.root)
    if written_by is None:
        findings.append(Finding(WARNING, f"{AGENTS_FILE} has no Dev Charter block, so coding agents do not know the "
                                "rules. Run `dev-charter sync`.", config.root / AGENTS_FILE))
    elif written_by != minor():
        findings.append(Finding(WARNING, f"The block in {AGENTS_FILE} was written by Dev Charter {written_by}; "
                                f"{minor()} is installed. Run `dev-charter sync`.", config.root / AGENTS_FILE))
    legacy = config.charter_dir / LEGACY_HANDOFF_FILE
    if legacy.exists():
        findings.append(Finding(WARNING, f"charter/{LEGACY_HANDOFF_FILE} is no longer used: each task card keeps its "
                                "own handoff now. Move its next step into the card it belongs to, then delete it.",
                                legacy))
    for repo in hooks.missing_checks(config):
        findings.append(Finding(WARNING, f"Commits to {repo.path.name} are not checked. Run `dev-charter sync` to add "
                                "the check.", repo.path))
    return _ordered(findings)


def _ordered(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (f.level != PROBLEM, str(f.path or ""), f.line or 0))


def _trace_findings(project: Project, trace: Trace, changes: dict[Path, str], staged: bool) -> list[Finding]:
    config = project.config
    entries = {e.id: e for e in project.entries}
    findings = []
    untagged_level = WARNING if config.mode == "light" else PROBLEM
    quiet_untagged = 0
    for code in trace.files:
        change = changes.get(code.absolute)
        if staged and change is None:
            continue
        for tag in code.tags:
            for ref in tag.refs:
                entry_id, _, letter = ref.partition(".")
                entry = entries.get(entry_id)
                if entry is None:
                    findings.append(Finding(PROBLEM, f"This code says it serves {ref}, but {entry_id} is not a feature "
                                            "or promise in charter/.", code.absolute, tag.line))
                elif letter and letter not in {c.letter for c in entry.criteria}:
                    findings.append(Finding(PROBLEM, f"This code says it serves {ref}, but {entry_id} has no check "
                                            f"'{letter}.' under Done means.", code.absolute, tag.line))
        if code.tags:
            continue
        if change == "new":
            findings.append(Finding(untagged_level, "This new code file does not say which feature it serves. Add a "
                                    "`serves: F-nnn — <what it is>` comment near the top (or `serves: foundation` for "
                                    "code every feature relies on).", code.absolute, 1))
        elif change == "changed":
            findings.append(Finding(WARNING, "This changed code file does not say which feature it serves. Add a "
                                    "`serves:` comment for the feature this change is for.", code.absolute, 1))
        else:
            quiet_untagged += 1
    if staged:
        return findings
    if quiet_untagged:
        findings.append(Finding(WARNING, f"{quiet_untagged} other code file(s) do not say which feature they serve; "
                                "the Code map in LEDGER.xlsx lists them as Unexplained."))

    for name in sorted({c.name for c in trace.results.cases for i in c.ids if i.split(".")[0] not in entries}):
        findings.append(Finding(WARNING, f"The test '{name}' names a feature or promise that is not in charter/."))
    for path, reason in trace.results.unreadable:
        findings.append(Finding(WARNING, f"These test results could not be read: {reason}.", path))
    for repo in config.repos:
        if not repo.results:
            continue
        files = [f for f in trace.results.files if f.repo == repo]
        if not files:
            findings.append(Finding(WARNING, f"No test results were found at {', '.join(repo.results)}; run the tests "
                                    "so they write them there.", repo.path))
            continue
        last_commit = git.commit_time(repo.path)
        newest = max(f.written for f in files).timestamp()
        if last_commit and newest < last_commit:
            findings.append(Finding(WARNING, f"The test results in {repo.path.name} are older than its latest commit; "
                                    "run the tests again so statuses are current.", files[0].path))
    if not any(repo.results for repo in config.repos):
        findings.append(Finding(WARNING, "No test results are configured, so statuses do not include any tests. Set "
                                "`results` in charter.toml to where your tests write JUnit XML."))
    return findings


def _internal_words(item_id: str, path: Path, texts: list[str], words: list[str]) -> list[Finding]:
    found = Counter()
    for word in words:
        pattern = re.compile(rf"(?<!\w){re.escape(word)}(?!\w)", re.IGNORECASE)
        for text in texts:
            found[word] += len(pattern.findall(text or ""))
    return [Finding(WARNING, f"{item_id} uses the in-house word '{word}'; say it in plain English.", path, None)
            for word, count in found.items() if count]
