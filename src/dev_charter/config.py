# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""charter.toml: finding the project, reading its settings, and writing them on `dev-charter init`."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

from . import __version__
from .errors import CharterError

CONFIG_FILE = "charter.toml"
CHARTER_DIR = "charter"
MODES = ("light", "standard", "strict")


@dataclass(frozen=True)
class Repo:
    path: Path  # absolute
    name: str = ""  # from charter.toml; otherwise taken from the git remote, then the folder
    url: str = ""  # the repository's web address, for links; otherwise taken from the git remote
    results: tuple[str, ...] = ()  # where its tests write JUnit XML, relative to the repository
    code: tuple[str, ...] = ()  # which files count as code, when the defaults do not fit
    tests: tuple[str, ...] = ()  # which files are tests, when the defaults do not fit


@dataclass(frozen=True)
class Config:
    root: Path
    product: str
    mode: str
    versions: str
    repos: tuple[Repo, ...]
    integration_branch: str = ""  # the branch work is merged into; empty means the remote's default branch
    roles: tuple[str, ...] = ()
    areas: tuple[str, ...] = ()
    internal_words: tuple[str, ...] = ()
    extra: dict = field(default_factory=dict)

    @property
    def charter_dir(self) -> Path:
        return self.root / CHARTER_DIR


def find_root(start: Path) -> Path:
    """The nearest folder at or above `start` that holds charter.toml."""
    start = start.resolve()
    for folder in (start, *start.parents):
        if (folder / CONFIG_FILE).is_file():
            return folder
    raise CharterError(
        f"No {CONFIG_FILE} found in {start} or any folder above it. "
        "Run `dev-charter init` in your product's root folder first."
    )


def version_range(version: str = __version__) -> str:
    """The range a new project pins: this minor version and its patches."""
    major, minor = Version(version).release[:2]
    return f">={major}.{minor},<{major}.{minor + 1}"


def load(root: Path) -> Config:
    path = root / CONFIG_FILE
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise CharterError(f"{path} could not be read: {exc}.") from exc

    product = data.get("product", {})
    name = str(product.get("name") or root.name)
    mode = str(product.get("mode") or "standard")
    if mode not in MODES:
        raise CharterError(f"{path}: mode is '{mode}'; it must be one of {', '.join(MODES)}.")
    versions = str(product.get("dev-charter") or "")

    repos = []
    for entry in data.get("repos") or [{"path": "."}]:
        repo_path = (root / str(entry.get("path", "."))).resolve()
        repos.append(
            Repo(
                path=repo_path,
                name=str(entry.get("name") or ""),
                url=str(entry.get("url") or "").rstrip("/"),
                results=_strings(entry.get("results")),
                code=_strings(entry.get("code")),
                tests=_strings(entry.get("tests")),
            )
        )

    words = data.get("words", {})
    return Config(
        root=root,
        product=name,
        mode=mode,
        versions=versions,
        repos=tuple(repos),
        integration_branch=str(product.get("integration_branch") or ""),
        roles=tuple(str(r) for r in words.get("roles") or ()),
        areas=tuple(str(a) for a in words.get("areas") or ()),
        internal_words=tuple(str(w) for w in words.get("internal") or ()),
        extra=data,
    )


def _strings(value) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value or ())


def check_version(config: Config, installed: str = __version__) -> None:
    """Refuse to run when this project was set up for a different Dev Charter."""
    if not config.versions:
        return
    try:
        spec = SpecifierSet(config.versions)
    except InvalidSpecifier as exc:
        raise CharterError(
            f"{CONFIG_FILE}: dev-charter = \"{config.versions}\" is not a version range Dev Charter understands."
        ) from exc
    if Version(Version(installed).base_version) not in spec:
        raise CharterError(
            f"This project uses Dev Charter {config.versions}, and Dev Charter {installed} is installed. "
            f"Install a matching version with `uv tool install \"dev-charter{config.versions}\"`, "
            f"or change the range in {CONFIG_FILE}."
        )


def _toml_list(values: list[str]) -> str:
    return "[" + ", ".join(json.dumps(v) for v in values) + "]"


def render(
    product: str,
    mode: str,
    repos: list[str],
    roles: list[str],
    areas: list[str],
    versions: str | None = None,
    integration_branch: str = "",
) -> str:
    """The text of a new charter.toml."""
    if mode not in MODES:
        raise CharterError(f"Mode '{mode}' is not one of {', '.join(MODES)}.")

    def noted(setting: str, note: str) -> str:
        return f"{setting:<32} # {note}"

    lines = [
        "# Dev Charter settings for this product. Edit freely; `dev-charter check` validates it.",
        "",
        "[product]",
        f"name = {json.dumps(product)}",
        noted(f"mode = {json.dumps(mode)}", "light | standard | strict"),
        noted(f"dev-charter = {json.dumps(versions or version_range())}",
              "the Dev Charter versions this project works with"),
        noted(f"integration_branch = {json.dumps(integration_branch)}",
              "the branch work is merged into; empty means the remote's default"),
        "",
    ]
    for repo in repos or ["."]:
        lines += [
            "[[repos]]",
            f"path = {json.dumps(repo)}",
            noted("results = []", "where this repo's tests write JUnit XML, e.g. \"reports/*.xml\""),
            "",
        ]
    lines += [
        "[words]",
        f"roles = {_toml_list(roles)}",
        f"areas = {_toml_list(areas)}",
        noted("internal = []", "in-house words that must not appear in plain-English text"),
        "",
    ]
    return "\n".join(lines)
