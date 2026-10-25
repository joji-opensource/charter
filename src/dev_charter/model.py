# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""What a charter is made of: features, promises, decisions, task cards and ideas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

STATES = ("idea", "agreed", "live", "parked", "retired")
PRIORITIES = ("Must", "Should", "Could")
CARD_STATES = ("open", "done")


@dataclass(frozen=True)
class Kind:
    """One kind of charter file: where it lives, how its IDs look, which labels its story uses."""

    name: str
    prefix: str
    folder: str
    labels: tuple[str, ...]
    required_labels: tuple[str, ...]
    has_criteria: bool

    def format_id(self, number: int) -> str:
        return f"{self.prefix}-{number:03d}"


FEATURE = Kind(
    name="feature",
    prefix="F",
    folder="features",
    labels=("As a", "I want to", "With", "Must also", "So that"),
    required_labels=("As a", "I want to", "So that"),
    has_criteria=True,
)
PROMISE = Kind(
    name="promise",
    prefix="P",
    folder="promises",
    labels=("We promise", "Applies to"),
    required_labels=("We promise",),
    has_criteria=True,
)
DECISION = Kind(
    name="decision",
    prefix="DEC",
    folder="decisions",
    labels=("Decision", "Instead of", "Because"),
    required_labels=("Decision", "Because"),
    has_criteria=False,
)
CARD = Kind(
    name="card",
    prefix="CARD",
    folder="cards",
    labels=("Goal",),
    required_labels=("Goal",),
    has_criteria=False,
)
KINDS = {kind.name: kind for kind in (FEATURE, PROMISE, DECISION, CARD)}


@dataclass(frozen=True)
class Criterion:
    letter: str
    text: str
    line: int


@dataclass(frozen=True)
class SignOff:
    on: date
    what: str  # a criterion letter, or "proven"
    person: str
    note: str
    line: int


@dataclass
class Entry:
    """A feature or a promise: something the product commits to, with checks that say when it is done."""

    kind: Kind
    id: str
    title: str
    state: str
    path: Path
    meta: dict
    story: dict[str, str]
    criteria: list[Criterion]
    signoffs: list[SignOff]
    words: int
    placeholders: list[tuple[int, str]] = field(default_factory=list)

    @property
    def area(self) -> str:
        return str(self.meta.get("area") or "")

    @property
    def priority(self) -> str:
        return str(self.meta.get("priority") or "")

    @property
    def release(self) -> str:
        return str(self.meta.get("release") or "")

    @property
    def decisions(self) -> list[str]:
        return [str(d) for d in self.meta.get("decisions") or []]

    def criterion_id(self, letter: str) -> str:
        return f"{self.id}.{letter}"


@dataclass
class Decision:
    id: str
    title: str
    path: Path
    on: date | None
    decided_by: str
    features: list[str]
    decision: str
    instead_of: str
    because: str


@dataclass
class Card:
    id: str
    title: str
    path: Path
    state: str
    serves: list[str]
    goal: str
    next_step: str = ""  # from the card's Handoff section
    allowed: tuple[str, ...] = ()  # the paths it may change, enforced in Strict mode


@dataclass(frozen=True)
class Idea:
    on: date | None
    text: str
    source: str
    line: int
