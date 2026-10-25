# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
from datetime import date
from pathlib import Path

import pytest

from dev_charter.model import FEATURE, Criterion, Entry, SignOff
from dev_charter.status import status


def entry(state="agreed", letters="abc", signed=()) -> Entry:
    return Entry(
        kind=FEATURE, id="F-014", title="Track my order", state=state, path=Path("F-014.md"), meta={}, story={},
        criteria=[Criterion(letter, "a check", 1) for letter in letters],
        signoffs=[SignOff(date(2026, 10, 24), what, "Joji John", "saw it", 1) for what in signed],
        words=0,
    )


GREEN = {"F-014.a": ["passed"], "F-014.c": ["passed"]}
C_RED = {"F-014.a": ["passed"], "F-014.c": ["failed"]}


@pytest.mark.parametrize(
    ("feature", "outcomes", "tagged", "expected"),
    [
        (entry(signed=("b", "proven")), GREEN, set(), ("Proven", 3)),
        (entry(signed=("b", "proven")), C_RED, set(), ("At risk", 2)),
        (entry(state="live", signed=("b",)), C_RED, set(), ("At risk", 2)),
        (entry(state="live"), GREEN, set(), ("Live", 2)),
        (entry(signed=("b",)), GREEN, set(), ("Built", 3)),
        (entry(), GREEN, set(), ("Being built", 2)),
        (entry(), C_RED, set(), ("Being built", 1)),
        (entry(), {}, {"F-014"}, ("Being built", 0)),
        (entry(), {}, set(), ("Agreed", 0)),
        (entry(), {"F-014.a": ["skipped"]}, set(), ("Being built", 0)),
        (entry(state="idea"), GREEN, set(), ("Idea", 2)),
        (entry(state="parked", signed=("proven",)), C_RED, set(), ("Parked", 1)),
        (entry(letters="", signed=("proven",)), {}, set(), ("Agreed", 0)),
    ],
)
def test_status_follows_the_rules_in_order(feature, outcomes, tagged, expected):
    result = status(feature, outcomes, tagged)
    assert (result.name, result.passing) == expected


def test_a_failed_test_outweighs_a_sign_off():
    result = status(entry(signed=("c",)), C_RED)
    assert result.criteria["c"] == "failing"


def test_the_check_count_reads_plainly():
    assert status(entry(), GREEN).checks == "2 of 3 checks passing"
    assert status(entry(letters="")).checks == "no checks yet"
