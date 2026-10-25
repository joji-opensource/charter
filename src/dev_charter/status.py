# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Status is worked out, never typed in: from the state people set, the test results and the sign-offs."""

from __future__ import annotations

from collections.abc import Mapping, Set
from dataclasses import dataclass

from .model import Entry

# The order statuses are listed in everywhere: what needs attention first.
ORDER = ("At risk", "Live", "Proven", "Built", "Being built", "Agreed", "Idea", "Parked", "Retired")
PASSING, FAILING, UNCHECKED = "passing", "failing", "unchecked"


@dataclass(frozen=True)
class Status:
    name: str
    passing: int
    total: int
    criteria: Mapping[str, str]  # check letter -> passing | failing | unchecked

    @property
    def checks(self) -> str:
        if self.total == 0:
            return "no checks yet"
        return f"{self.passing} of {self.total} checks passing"


def criterion_states(entry: Entry, outcomes: Mapping[str, list[str]]) -> dict[str, str]:
    """Each check is failing if any of its tests failed, passing if a test passed or a person signed it off."""
    signed = {s.what for s in entry.signoffs}
    states = {}
    for criterion in entry.criteria:
        runs = outcomes.get(entry.criterion_id(criterion.letter), [])
        if "failed" in runs:
            states[criterion.letter] = FAILING
        elif "passed" in runs or criterion.letter in signed:
            states[criterion.letter] = PASSING
        else:
            states[criterion.letter] = UNCHECKED
    return states


def status(entry: Entry, outcomes: Mapping[str, list[str]] | None = None, tagged: Set[str] = frozenset()) -> Status:
    """The first rule that matches wins (plan §5.4)."""
    outcomes = outcomes or {}
    states = criterion_states(entry, outcomes)
    passing = sum(1 for s in states.values() if s == PASSING)
    total = len(states)
    all_passing = total > 0 and passing == total
    failing = FAILING in states.values()
    proven = any(s.what == "proven" for s in entry.signoffs)
    live = entry.state == "live"
    has_tests = any(key == entry.id or key.startswith(entry.id + ".") for key in outcomes)

    if entry.state in ("idea", "parked", "retired"):
        name = entry.state.capitalize()
    elif failing and (live or proven):
        name = "At risk"
    elif live:
        name = "Live"
    elif all_passing and proven:
        name = "Proven"
    elif all_passing:
        name = "Built"
    elif entry.id in tagged or has_tests:
        name = "Being built"
    else:
        name = "Agreed"
    return Status(name, passing, total, states)
