# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The few questions Dev Charter asks git. Every answer is None or empty when git cannot answer."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def run(folder: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(folder), *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def toplevel(folder: Path) -> Path | None:
    out = run(folder, "rev-parse", "--show-toplevel")
    return Path(out.strip()).resolve() if out else None


def prefix(folder: Path) -> str:
    """The folder's path inside its repository, such as 'examples/demo-store/' (empty at the top)."""
    return (run(folder, "rev-parse", "--show-prefix") or "").strip()


def head(folder: Path) -> str | None:
    out = run(folder, "rev-parse", "HEAD")
    return out.strip() if out else None


def commit_time(folder: Path) -> float | None:
    out = run(folder, "log", "-1", "--format=%ct")
    return float(out.strip()) if out and out.strip() else None


def is_pushed(folder: Path, commit: str) -> bool:
    """Whether a remote branch already has this commit, so a link to it will open."""
    return bool((run(folder, "branch", "-r", "--contains", commit) or "").strip())


def files(folder: Path) -> tuple[list[str], set[str]] | None:
    """Every file git would keep (tracked and new), relative to `folder`, and which of them are not yet tracked."""
    tracked = run(folder, "ls-files", "--cached")
    if tracked is None:
        return None
    new = run(folder, "ls-files", "--others", "--exclude-standard") or ""
    untracked = {line for line in new.splitlines() if line}
    listed = [line for line in tracked.splitlines() if line] + sorted(untracked)
    return listed, untracked


def changes(folder: Path, staged: bool) -> dict[str, str]:
    """Code changes relative to `folder`: path -> 'new' or 'changed'. Staged: what is about to be committed."""
    if staged:
        out = run(folder, "diff", "--cached", "--name-status", "--relative", "--diff-filter=ACMR") or ""
        result = {}
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                result[parts[-1]] = "new" if parts[0][0] in "AC" else "changed"
        return result
    out = run(folder, "status", "--porcelain", "--untracked-files=all", "--", ".") or ""
    pre = prefix(folder)
    result = {}
    for line in out.splitlines():
        code, path = line[:2], line[3:].split(" -> ")[-1].strip('"')
        if pre and path.startswith(pre):
            path = path[len(pre):]
        if code in ("??", "A ", "AM"):
            result[path] = "new"
        elif "M" in code or "R" in code:
            result[path] = "changed"
    return result


def hooks_dir(folder: Path) -> Path | None:
    out = run(folder, "rev-parse", "--git-path", "hooks")
    if not out:
        return None
    path = Path(out.strip())
    return (folder / path).resolve() if not path.is_absolute() else path


def web_url(folder: Path) -> str:
    """The repository's web address from its `origin` remote, such as https://github.com/owner/repo."""
    remote = (run(folder, "remote", "get-url", "origin") or "").strip()
    if not remote:
        return ""
    match = re.match(r"^(?:ssh://)?git@([^:/]+)[:/](.+?)(?:\.git)?/?$", remote)
    if match:
        return f"https://{match.group(1)}/{match.group(2)}"
    match = re.match(r"^https?://(?:[^@/]+@)?(.+?)(?:\.git)?/?$", remote)
    return f"https://{match.group(1)}" if match else ""


def file_link(base: str, commit: str, path: str) -> str:
    """A link that opens `path` at `commit` on the repository's website."""
    if "gitlab" in base:
        return f"{base}/-/blob/{commit}/{path}"
    if "bitbucket" in base:
        return f"{base}/src/{commit}/{path}"
    return f"{base}/blob/{commit}/{path}"
