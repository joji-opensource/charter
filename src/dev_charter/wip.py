# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Work in progress: the open task cards on other people's branches, read from git without checking anything out."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import git
from .config import CHARTER_DIR, Config
from .errors import FileProblem
from .model import CARD, Card
from .store import read_card

MAX_BRANCHES = 30
MAX_AGE_DAYS = 60


@dataclass
class BranchWork:
    branch: git.Branch
    ahead: int
    cards: list[Card] = field(default_factory=list)

    @property
    def when(self) -> datetime:
        return datetime.fromtimestamp(self.branch.when)


@dataclass
class WorkInProgress:
    base: str | None  # the integration branch compared against
    fetched: datetime | None
    branches: list[BranchWork] = field(default_factory=list)


def collect(config: Config) -> WorkInProgress:
    root = config.root
    if git.toplevel(root) is None:
        return WorkInProgress(None, None)
    base = git.integration_branch(root, config.integration_branch)
    fetched = git.last_fetch(root)
    found = WorkInProgress(base, datetime.fromtimestamp(fetched) if fetched else None)
    if base is None:
        return found
    base_name = base.split("/", 1)[1] if base.startswith("origin/") else base
    current = git.current_branch(root)
    oldest = time.time() - MAX_AGE_DAYS * 86400
    cards_path = f"{CHARTER_DIR}/{CARD.folder}"
    candidates = []
    for branch in git.branches(root):
        if branch.name in (base_name, current) or branch.when < oldest:
            continue
        ahead = git.ahead(root, base, branch.ref)
        if not ahead:
            continue
        changed = git.changed_since_fork(root, base, branch.ref, cards_path)
        candidates.append((branch, ahead, changed))
        if len(candidates) == MAX_BRANCHES:
            break
    specs = [f"{branch.ref}:{path}" for branch, _, changed in candidates for path in changed]
    texts = git.read_many(root, specs)
    for branch, ahead, changed in candidates:
        work = BranchWork(branch, ahead)
        for path in changed:
            text = texts.get(f"{branch.ref}:{path}")
            if not text:
                continue
            try:
                card = read_card(Path(path), text)
            except FileProblem:
                continue
            if card.state == "open":
                work.cards.append(card)
        if work.cards:
            found.branches.append(work)
    return found
