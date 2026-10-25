# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Test results: which checks passed or failed, read from the JUnit XML most test runners write."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import Config, Repo

# The prefix is upper case and may follow a lower-case letter (TestF014B, testF014bSendsText); a check letter must
# not run on into a lower-case word, so F014_order is F-014 and f401 is nothing.
TEST_ID_RE = re.compile(r"(?<![A-Z0-9])([FP])-?(\d{3,})(?:[._-]?([a-zA-Z]))?(?![a-z0-9])")
PARAMETERS_RE = re.compile(r"\[.*\]$")


@dataclass(frozen=True)
class TestCase:
    __test__ = False  # a test result, not a test for pytest to collect

    name: str
    outcome: str  # passed | failed | skipped
    ids: tuple[str, ...]  # "F-014.b", or "F-014" when the name has no check letter
    source: Path


@dataclass(frozen=True)
class ResultsFile:
    repo: Repo
    path: Path
    written: datetime


@dataclass
class Results:
    cases: list[TestCase] = field(default_factory=list)
    files: list[ResultsFile] = field(default_factory=list)
    unreadable: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def outcomes(self) -> dict[str, list[str]]:
        """Each check or feature ID mapped to the outcomes of the tests named after it."""
        found: dict[str, list[str]] = {}
        for case in self.cases:
            for test_id in case.ids:
                found.setdefault(test_id, []).append(case.outcome)
        return found

    def for_entry(self, entry_id: str) -> list[TestCase]:
        return [c for c in self.cases if any(i == entry_id or i.startswith(entry_id + ".") for i in c.ids)]


def ids_in(name: str) -> tuple[str, ...]:
    """The feature and check IDs in a test's name, ignoring any parameters in brackets."""
    name = PARAMETERS_RE.sub("", name)
    found = []
    for match in TEST_ID_RE.finditer(name):
        test_id = f"{match.group(1)}-{match.group(2)}"
        if match.group(3):
            test_id += f".{match.group(3).lower()}"
        found.append(test_id)
    return tuple(dict.fromkeys(found))


def _outcome(case: ET.Element) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return "failed"
    if case.find("skipped") is not None:
        return "skipped"
    return "passed"


def result_files(repo: Repo) -> list[Path]:
    return sorted({path for pattern in repo.results for path in repo.path.glob(pattern) if path.is_file()})


def read(config: Config) -> Results:
    results = Results()
    for repo in config.repos:
        for path in result_files(repo):
            try:
                tree = ET.parse(path)
            except (ET.ParseError, OSError) as exc:
                results.unreadable.append((path, str(exc)))
                continue
            results.files.append(ResultsFile(repo, path, datetime.fromtimestamp(path.stat().st_mtime)))
            for case in tree.iter("testcase"):
                name = case.get("name", "")
                results.cases.append(TestCase(name, _outcome(case), ids_in(name), path))
    return results
