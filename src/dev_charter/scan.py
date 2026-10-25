# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Which code serves which feature: the `serves:` tags in each repository's code files."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import git
from .config import CHARTER_DIR, Repo

SOURCE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".go", ".rs", ".java", ".kt",
    ".kts", ".scala", ".rb", ".php", ".cs", ".fs", ".swift", ".m", ".mm", ".c", ".h", ".cc", ".cpp", ".hpp", ".dart",
    ".ex", ".exs", ".erl", ".clj", ".lua", ".r", ".sql", ".sh",
}
TEST_FOLDERS = {"test", "tests", "__tests__", "spec", "specs", "testing"}
SKIPPED_FOLDERS = {"node_modules", ".venv", "venv", "dist", "build", "vendor", "__pycache__", ".git", CHARTER_DIR}
MAX_BYTES = 2_000_000

SERVES_RE = re.compile(r"serves:\s*([^\n]*)", re.IGNORECASE)
TAG_ID_RE = re.compile(r"(?<![A-Za-z0-9])([FP]-\d{3,})(?:\.[a-z])?(?![A-Za-z0-9])")
FOUNDATION_RE = re.compile(r"^foundation\b", re.IGNORECASE)


@dataclass(frozen=True)
class Tag:
    ids: tuple[str, ...]
    foundation: bool
    line: int


@dataclass(frozen=True)
class CodeFile:
    repo: RepoInfo
    path: str  # relative to the repository folder, with forward slashes
    tag: Tag | None
    untracked: bool

    @property
    def serves(self) -> tuple[str, ...]:
        return self.tag.ids if self.tag else ()

    @property
    def kind(self) -> str:
        if self.tag and self.tag.ids:
            return "Feature code"
        if self.tag and self.tag.foundation:
            return "Shared foundation"
        return "Unexplained"

    @property
    def absolute(self) -> Path:
        return self.repo.repo.path / self.path

    @property
    def link(self) -> str:
        """A link to this file on the repository's website at the scanned commit, or '' when it would not open."""
        info = self.repo
        if not (info.url and info.commit and info.pushed) or self.untracked:
            return ""
        return git.file_link(info.url, info.commit, info.prefix + self.path)


@dataclass(frozen=True)
class RepoInfo:
    repo: Repo
    name: str
    url: str
    commit: str | None
    pushed: bool
    prefix: str  # the repository folder's path inside its git repository
    is_git: bool


def describe(repo: Repo) -> RepoInfo:
    top = git.toplevel(repo.path)
    commit = git.head(repo.path) if top else None
    url = repo.url or (git.web_url(repo.path) if top else "")
    name = repo.name or (url.rsplit("/", 1)[-1] if url else "") or repo.path.name
    return RepoInfo(
        repo=repo,
        name=name,
        url=url,
        commit=commit,
        pushed=bool(commit) and git.is_pushed(repo.path, commit),
        prefix=git.prefix(repo.path) if top else "",
        is_git=top is not None,
    )


def _glob_re(pattern: str) -> re.Pattern:
    """A glob with ** (any folders), * and ? as a regular expression over forward-slash paths."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(_glob_re(p).match(path) for p in patterns)


def is_test(path: str, repo: Repo) -> bool:
    if repo.tests:
        return matches(path, repo.tests)
    pure = PurePosixPath(path)
    name = pure.name.lower()
    return (
        any(part.lower() in TEST_FOLDERS for part in pure.parts[:-1])
        or name.startswith("test_")
        or pure.stem.lower().endswith(("_test", ".test", ".spec", "_spec"))
    )


def is_code(path: str, repo: Repo) -> bool:
    if is_test(path, repo):
        return False
    if repo.code:
        return matches(path, repo.code)
    pure = PurePosixPath(path)
    if any(part in SKIPPED_FOLDERS or part.startswith(".") for part in pure.parts[:-1]):
        return False
    return pure.suffix.lower() in SOURCE_EXTENSIONS


def read_tag(text: str) -> Tag | None:
    """The first `serves:` line that names an ID or `foundation`; prose that merely says 'serves:' is ignored."""
    for match in SERVES_RE.finditer(text):
        rest = match.group(1)
        ids = tuple(dict.fromkeys(m.group(1) for m in TAG_ID_RE.finditer(rest)))
        foundation = bool(FOUNDATION_RE.match(rest.strip()))
        if ids or foundation:
            return Tag(ids, foundation and not ids, text.count("\n", 0, match.start()) + 1)
    return None


def _walk(folder: Path) -> list[str]:
    found = []
    for current, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIPPED_FOLDERS and not d.startswith(".")]
        for name in names:
            found.append((Path(current) / name).relative_to(folder).as_posix())
    return sorted(found)


def scan_repo(info: RepoInfo) -> list[CodeFile]:
    repo = info.repo
    listed = git.files(repo.path) if info.is_git else None
    paths, untracked = listed if listed is not None else (_walk(repo.path), set())
    found = []
    for rel in paths:
        if not is_code(rel, repo):
            continue
        path = repo.path / rel
        try:
            if not path.is_file() or path.stat().st_size > MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found.append(CodeFile(info, rel, read_tag(text), rel in untracked))
    return found
