# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The trace: the code tagged with each feature, and the results of the tests named after its checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import results as results_module
from . import scan
from .config import Config
from .results import Results, TestCase
from .scan import CodeFile, RepoInfo


@dataclass
class Trace:
    repos: list[RepoInfo] = field(default_factory=list)
    files: list[CodeFile] = field(default_factory=list)
    results: Results = field(default_factory=Results)

    @property
    def tagged(self) -> set[str]:
        return {entry_id for f in self.files for entry_id in f.serves}

    @property
    def outcomes(self) -> dict[str, list[str]]:
        return self.results.outcomes

    def built_in(self, entry_id: str) -> list[CodeFile]:
        return [f for f in self.files if entry_id in f.serves]

    def code_for(self, check_id: str) -> list[tuple[CodeFile, int]]:
        """The files and lines tagged with one check, such as F-014.c."""
        return [(f, tag.line) for f in self.files for tag in f.tags if check_id in tag.refs]

    def tests_for(self, entry_id: str) -> list[TestCase]:
        return self.results.for_entry(entry_id)


def collect(config: Config) -> Trace:
    trace = Trace()
    for repo in config.repos:
        info = scan.describe(repo)
        trace.repos.append(info)
        trace.files.extend(scan.scan_repo(info))
    trace.results = results_module.read(config)
    return trace
