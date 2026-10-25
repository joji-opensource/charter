# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Git hooks: check each commit before it is made, and rebuild the spreadsheet after."""

from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path

from . import git
from .config import Config, Repo

MARKER = "# dev-charter hook"
PRE_COMMIT, POST_COMMIT = "pre-commit", "post-commit"
INSTALL_HINT = "uv tool install dev-charter"


def _executable() -> str:
    """Where this dev-charter is installed, for commits made from apps whose PATH does not include it."""
    found = shutil.which("dev-charter")
    if found:
        return str(Path(found).resolve())
    argv0 = Path(sys.argv[0])
    return str(argv0.resolve()) if argv0.name == "dev-charter" and argv0.exists() else ""


def script(kind: str, root_from_repo: str) -> str:
    finder = (f'DC="$(command -v dev-charter || true)"\n'
              f'[ -n "$DC" ] || DC={shlex.quote(_executable())}\n')
    root = shlex.quote(root_from_repo)
    if kind == PRE_COMMIT:
        return (f"#!/bin/sh\n{MARKER}: checks each commit against the product's charter. "
                "Managed by `dev-charter sync`.\n"
                f"{finder}"
                f'if [ -x "$DC" ]; then\n  exec "$DC" --root {root} check --staged\nfi\n'
                f'echo "Dev Charter is not installed, so this commit was not checked. Install it with: '
                f'{INSTALL_HINT}" >&2\nexit 0\n')
    return (f"#!/bin/sh\n{MARKER}: rebuilds LEDGER.xlsx and status.html after each commit. "
            "Managed by `dev-charter sync`.\n"
            f"{finder}"
            f'[ -x "$DC" ] && "$DC" --root {root} report --quiet\nexit 0\n')


def wanted(config: Config) -> tuple[str, ...]:
    return (POST_COMMIT,) if config.mode == "light" else (PRE_COMMIT, POST_COMMIT)


def _manual_line(kind: str, root_from_repo: str) -> str:
    command = "check --staged" if kind == PRE_COMMIT else "report --quiet"
    return f"dev-charter --root {shlex.quote(root_from_repo)} {command}"


def _where(config: Config, repo: Repo) -> str:
    try:
        relative = repo.path.relative_to(config.root).as_posix()
    except ValueError:
        return str(repo.path)
    return "This folder" if relative in ("", ".") else relative


def install(config: Config) -> list[str]:
    """Install or refresh the hooks in every repository; returns one plain line per thing done or not done."""
    notes = []
    for repo in config.repos:
        where = _where(config, repo)
        top = git.toplevel(repo.path)
        if top is None:
            notes.append(f"{where} is not a git repository, so its commits are not checked.")
            continue
        if top != repo.path.resolve():
            notes.append(f"{where} is a folder inside the git repository at {top}, not the top of one, so no commit "
                         "checks were installed there.")
            continue
        folder = git.hooks_dir(repo.path)
        if folder is None:
            notes.append(f"{where}: git did not say where its hooks live, so no commit checks were installed.")
            continue
        folder.mkdir(parents=True, exist_ok=True)
        root_from_repo = os.path.relpath(config.root, repo.path)
        uses_framework = (repo.path / ".pre-commit-config.yaml").exists()
        for kind in (PRE_COMMIT, POST_COMMIT):
            path = folder / kind
            ours = path.is_file() and MARKER in path.read_text(encoding="utf-8", errors="replace")
            if kind not in wanted(config):
                if ours:
                    path.unlink()
                    notes.append(f"{where}: removed the {kind} check ({config.mode} mode checks in CI only).")
                continue
            if kind == PRE_COMMIT and uses_framework and not ours:
                notes.append(f"{where} uses the pre-commit framework: add a local hook that runs "
                             f"`{_manual_line(kind, root_from_repo)}`.")
                continue
            if path.exists() and not ours:
                notes.append(f"{where} already has a {kind} hook, left as it is: add the line "
                             f"`{_manual_line(kind, root_from_repo)}` to {path}.")
                continue
            text = script(kind, root_from_repo)
            if ours and path.read_text(encoding="utf-8") == text:
                continue
            path.write_text(text, encoding="utf-8")
            path.chmod(0o755)
            notes.append(f"{where}: {'refreshed' if ours else 'installed'} the {kind} hook.")
    return notes


def missing_checks(config: Config) -> list[Repo]:
    """Repositories that should check each commit and do not."""
    if PRE_COMMIT not in wanted(config):
        return []
    lacking = []
    for repo in config.repos:
        if git.toplevel(repo.path) != repo.path.resolve():
            continue
        folder = git.hooks_dir(repo.path)
        path = folder / PRE_COMMIT if folder else None
        text = path.read_text(encoding="utf-8", errors="replace") if path and path.is_file() else ""
        config_file = repo.path / ".pre-commit-config.yaml"
        if config_file.exists():
            text += config_file.read_text(encoding="utf-8", errors="replace")
        if "dev-charter" not in text or "check --staged" not in text:
            lacking.append(repo)
    return lacking
