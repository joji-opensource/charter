# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Publishing the team's ledger: LEDGER.xlsx and status.html on their own branch, readable by whoever can read the
repository, updated by CI after each merge."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .config import Config
from .errors import CharterError
from .report import GENERATED

LEDGER_BRANCH = "ledger"
README = (b"# The team's ledger\n\nBuilt by Dev Charter from the integration branch after each merge. Download "
          b"LEDGER.xlsx, or open status.html. Do not edit: change the files in charter/ instead.\n")


def _git(folder: Path, *args: str, data: bytes | None = None, env: dict | None = None) -> str:
    result = subprocess.run(["git", "-C", str(folder), *args], input=data, capture_output=True, env=env)
    if result.returncode != 0:
        raise CharterError(f"git {args[0]} failed: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout.decode().strip()


def publish(config: Config, branch: str = LEDGER_BRANCH, push: bool = True) -> str:
    """Commit the generated files to `branch` (on top of its last commit, if any) and push it. Returns the commit."""
    root = config.root
    files = [root / name for name in GENERATED]
    missing = [f.name for f in files if not f.exists()]
    if missing:
        raise CharterError(f"{', '.join(missing)} not found; run `dev-charter report` first.")
    entries = []
    for path in files:
        blob = _git(root, "hash-object", "-w", "--stdin", data=path.read_bytes())
        entries.append(f"100644 blob {blob}\t{path.name}")
    readme = _git(root, "hash-object", "-w", "--stdin", data=README)
    entries.append(f"100644 blob {readme}\tREADME.md")
    tree = _git(root, "mktree", data=("\n".join(entries) + "\n").encode())
    parent = ""
    for ref in (f"refs/remotes/origin/{branch}", f"refs/heads/{branch}"):
        try:
            parent = _git(root, "rev-parse", "--verify", "-q", ref)
            break
        except CharterError:
            continue
    source = _git(root, "rev-parse", "--short", "HEAD")
    env = {**os.environ, "GIT_AUTHOR_NAME": "Dev Charter", "GIT_AUTHOR_EMAIL": "dev-charter@users.noreply.github.com",
           "GIT_COMMITTER_NAME": "Dev Charter", "GIT_COMMITTER_EMAIL": "dev-charter@users.noreply.github.com"}
    commit = _git(root, "commit-tree", tree, *(["-p", parent] if parent else []),
                  "-m", f"Ledger built from {source}", env=env)
    _git(root, "update-ref", f"refs/heads/{branch}", commit)
    if push:
        _git(root, "push", "origin", f"{commit}:refs/heads/{branch}")
    return commit
