# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The stage guides, shipped inside the package so every project gets the same ones."""

from importlib.resources import files

STAGES = {
    "principles": "the rules that apply at every stage",
    "feature": "turn a request into a feature or a promise",
    "plan": "write a file-level plan the person approves before any code",
    "review": "review the plan twice, problems first",
    "probe": "prove the plan's risky assumptions against real code and data",
    "build": "build only what the task card serves, reversibly",
    "verify": "prove the work on a real run",
    "ship": "hand off, and prepare the commit",
    "commands": "every dev-charter command, and when to use it",
}


def read(stage: str) -> str:
    return files(__name__).joinpath(f"{stage}.md").read_text(encoding="utf-8")
