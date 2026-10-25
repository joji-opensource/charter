# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The few questions Dev Charter asks git. Every answer is None or empty when git cannot answer."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
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


def names_in_history(folder: Path, path: str) -> set[str]:
    """The name of every file that has ever been under `path`, on any branch, stash or tag, including deleted ones."""
    out = run(folder, "log", "--all", "--name-only", "--format=", "--", path) or ""
    return {Path(line).name for line in out.splitlines() if line.strip()}


def last_fetch(folder: Path) -> float | None:
    """When this clone last fetched from its remote, as a timestamp."""
    out = run(folder, "rev-parse", "--git-path", "FETCH_HEAD")
    if not out:
        return None
    path = Path(out.strip())
    path = path if path.is_absolute() else folder / path
    return path.stat().st_mtime if path.exists() else None


def has_remote(folder: Path) -> bool:
    return bool((run(folder, "remote") or "").strip())


def current_branch(folder: Path) -> str:
    return (run(folder, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()


def exists(folder: Path, ref: str) -> bool:
    return run(folder, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}") is not None


def integration_branch(folder: Path, configured: str = "") -> str | None:
    """The branch work is merged into: the configured one, else the remote's default branch, else main, else master.

    Returns the ref to compare against, preferring the remote's copy because that is what everyone shares.
    """
    names = [configured] if configured else []
    remote_head = (run(folder, "symbolic-ref", "--short", "refs/remotes/origin/HEAD") or "").strip()
    if remote_head:
        names.append(remote_head.removeprefix("origin/"))
    names += ["main", "master"]
    for name in names:
        for ref in (f"origin/{name}", name):
            if exists(folder, ref):
                return ref
    return None


@dataclass(frozen=True)
class Branch:
    name: str
    ref: str
    commit: str
    when: float
    author: str
    pushed: bool  # a remote copy exists and holds this same commit


def branches(folder: Path) -> list[Branch]:
    """Local and remote branches, one per name (the newer copy), newest first."""
    out = run(folder, "for-each-ref", "refs/heads", "refs/remotes", "--sort=-committerdate",
              "--format=%(refname)\t%(objectname)\t%(committerdate:unix)\t%(authorname)") or ""
    remote_commits: dict[str, str] = {}
    rows = []
    for line in out.splitlines():
        full, commit, when, author = line.split("\t")
        if full.startswith("refs/remotes/"):
            remote, _, name = full.removeprefix("refs/remotes/").partition("/")
            if not name or name == "HEAD":
                continue
            remote_commits.setdefault(name, commit)
            ref = f"{remote}/{name}"
        else:
            name = ref = full.removeprefix("refs/heads/")
        rows.append((name, ref, commit, float(when or 0), author))
    seen: dict[str, Branch] = {}
    for name, ref, commit, when, author in rows:
        if name not in seen:
            seen[name] = Branch(name, ref, commit, when, author, remote_commits.get(name) == commit)
    return list(seen.values())


def ahead(folder: Path, base: str, ref: str) -> int:
    """How many commits `ref` has that `base` does not."""
    out = (run(folder, "rev-list", "--left-right", "--count", f"{base}...{ref}") or "").split()
    return int(out[1]) if len(out) == 2 else 0


def changed_since_fork(folder: Path, base: str, ref: str, path: str) -> list[str]:
    """Files under `path` that `ref` added or changed since it left `base` (paths from the repository's top)."""
    out = run(folder, "diff", "--name-only", "--diff-filter=AMR", f"{base}...{ref}", "--", path) or ""
    return [line for line in out.splitlines() if line]


def files_at(folder: Path, ref: str, path: str) -> list[str]:
    """Files under `path` at `ref` (paths from the repository's top)."""
    out = run(folder, "ls-tree", "-r", "--name-only", "--full-name", ref, "--", path) or ""
    return [line for line in out.splitlines() if line]


def read_many(folder: Path, specs: list[str]) -> dict[str, str | None]:
    """Read many `ref:path` files in one git process. Missing files read as None."""
    if not specs:
        return {}
    try:
        result = subprocess.run(["git", "-C", str(folder), "cat-file", "--batch"],
                                input=("\n".join(specs) + "\n").encode(), capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return dict.fromkeys(specs)
    out, position, found = result.stdout, 0, {}
    for spec in specs:
        end = out.index(b"\n", position)
        header = out[position:end].decode()
        position = end + 1
        if header.endswith("missing") or header.endswith("ambiguous"):
            found[spec] = None
            continue
        size = int(header.split()[2])
        found[spec] = out[position:position + size].decode("utf-8", errors="replace")
        position += size + 1
    return found


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
