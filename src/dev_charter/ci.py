# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""`dev-charter ci`: the GitHub workflow that checks each pull request and keeps the team's ledger up to date."""

from __future__ import annotations

import re
from pathlib import Path

from . import git
from .config import Config, version_range
from .errors import CharterError

WORKFLOW = ".github/workflows/dev-charter.yml"
INSTALL_RE = re.compile(r'uv tool install "dev-charter(?P<range>[^"]*)"')
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1"
SETUP_UV = "astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e # v10.3.2"


def test_command(config: Config) -> str:
    """The step that runs the product's tests so they write JUnit XML; a person adjusts it to their project."""
    if (config.root / "pyproject.toml").exists():
        return "uv run pytest --junitxml=reports/junit.xml"
    return ('echo "Edit this step in .github/workflows/dev-charter.yml to run your tests, writing JUnit XML where '
            'charter.toml\'s results say." && exit 1')


def render(config: Config, branch: str) -> str:
    return f"""# Dev Charter: checks each pull request against the product's charter, and keeps the team's ledger
# (LEDGER.xlsx and status.html) on the `ledger` branch after each merge. Written by `dev-charter ci`.
# Edit the "Run the tests" step to run your own tests.
name: dev-charter

on:
  pull_request:
  push:
    branches: [{branch}]

permissions: {{}}

jobs:
  charter:
    runs-on: ubuntu-latest
    permissions:
      contents: write        # to update the ledger branch
      pull-requests: write   # to post the summary on the pull request
    steps:
      - uses: {CHECKOUT}
        with:
          fetch-depth: 0
      - uses: {SETUP_UV}
      - name: Install Dev Charter
        run: uv tool install "dev-charter{config.versions or version_range()}"
      - name: Run the tests, writing JUnit XML where charter.toml says
        run: {test_command(config)}
        continue-on-error: true  # a failing test shows as At risk in the ledger; it never stops the ledger
      - name: Summarise and check the pull request
        if: github.event_name == 'pull_request'
        run: dev-charter pr-summary --base "origin/${{{{ github.base_ref }}}}" --comment
        env:
          GH_TOKEN: ${{{{ github.token }}}}
          PR_NUMBER: ${{{{ github.event.pull_request.number }}}}
      - name: Publish the team's ledger
        if: github.event_name == 'push'
        run: dev-charter report && dev-charter publish
"""


def write(config: Config) -> tuple[Path, str]:
    top = git.toplevel(config.root)
    if top is None or top != config.root.resolve():
        raise CharterError("The workflow goes at the top of the product's own git repository; this folder is not one.")
    branch = config.integration_branch or (git.integration_branch(config.root) or "main").removeprefix("origin/")
    path = config.root / WORKFLOW
    text = render(config, branch)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return path, "unchanged"
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, "updated" if existed else "created"


def upgrade_install(config: Config, versions: str) -> str | None:
    """Point the workflow `dev-charter ci` wrote at these versions, changing only its install line; a workflow whose
    install line was changed by hand is left alone, and the person is told."""
    path = config.root / WORKFLOW
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    found = INSTALL_RE.findall(text)
    if len(found) != 1:
        return (f"{WORKFLOW}: its install line is not the one `dev-charter ci` wrote, so it was left as it is; make "
                f"it install \"dev-charter{versions}\".")
    if found[0] == versions:
        return None
    path.write_text(INSTALL_RE.sub(f'uv tool install "dev-charter{versions}"', text, count=1), encoding="utf-8")
    return f"{WORKFLOW}: now installs Dev Charter {versions}."
