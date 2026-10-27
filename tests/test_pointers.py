# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Codex in a product of several repositories (0.2): a pointer to the rules where Codex would not find them, a write
the system refuses said in plain words, and guides that name an agent only where what to do differs."""

import re
import subprocess
from pathlib import Path

import pytest

from dev_charter import agents
from dev_charter.config import find_root, load

from .conftest import Product

GUIDES = Path(__file__).resolve().parents[1] / "src/dev_charter"


def git_init(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(folder)], check=True)


@pytest.fixture
def several(tmp_path: Path) -> Product:
    """A product whose root is a git repository holding a child repository (ignored by the root, like a nested
    service) and a plain folder inside the root's repository."""
    root = tmp_path / "store"
    git_init(root)
    git_init(root / "api")
    (root / "web").mkdir()
    (root / ".gitignore").write_text("/api/\n")
    shop = Product(root)
    shop.run("init", "--name", "Demo Store", "--repo", ".", "--repo", "api", "--repo", "web", "--yes")
    return shop


def test_a_pointer_goes_only_where_codex_would_not_find_the_rules(several: Product):
    root = several.root
    pointer = (root / "api/AGENTS.md").read_text()
    assert "This folder is part of Demo Store. Its rules are in `../AGENTS.md`: read that file now" in pointer
    assert pointer.startswith("<!-- dev-charter:start v") and pointer.rstrip().endswith(agents.END)
    assert not (root / "web/AGENTS.md").exists(), "Codex started in web/ walks down from the root and finds them"
    assert "Dev Charter section" not in several.run("check").output and "pointer" not in several.run("check").output

    sync = several.run("sync").output
    assert "api/AGENTS.md" not in sync, "unchanged, so not mentioned"
    (root / "api/AGENTS.md").write_text("# The API's own rules\n")
    assert "api/AGENTS.md has no pointer to Demo Store's rules" in several.run("check").output
    assert "api/AGENTS.md: updated the pointer to Demo Store's rules." in several.run("sync").output
    assert (root / "api/AGENTS.md").read_text().startswith("# The API's own rules\n\n<!-- dev-charter:start")


def test_a_product_outside_git_gets_a_pointer_in_each_listed_folder(tmp_path: Path):
    (tmp_path / "shop/app").mkdir(parents=True)
    Product(tmp_path / "shop").run("init", "--name", "Demo Store", "--repo", ".", "--repo", "app", "--yes")
    assert "Its rules are in `../AGENTS.md`" in (tmp_path / "shop/app/AGENTS.md").read_text()


def test_check_says_when_codex_would_read_something_else(several: Product):
    root = several.root
    (root / "api" / agents.OVERRIDE_FILE).write_text("# local\n")
    assert f"Codex reads {agents.OVERRIDE_FILE} instead of AGENTS.md in this folder" in several.run("check").output
    (root / "api" / agents.OVERRIDE_FILE).unlink()
    agents_md = root / "AGENTS.md"
    agents_md.write_text("# Long house rules\n" + "x" * (agents.CODEX_LIMIT + 10) + "\n\n" + agents_md.read_text())
    assert "The Dev Charter section in AGENTS.md starts after the first 32 KiB" in several.run("check").output


def test_pointer_folders_follow_where_codex_looks(several: Product):
    found = agents.pointer_folders(load(find_root(several.root)))
    assert [(folder.name, to_root) for folder, to_root in found] == [("api", "..")]


def test_a_refused_write_is_said_plainly(several: Product, monkeypatch: pytest.MonkeyPatch):
    cards = several.root / "charter/cards"
    cards.chmod(0o555)
    try:
        for name in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID"):
            monkeypatch.delenv(name, raising=False)
        said = several.run("card", "new", "Order page", ok=False).output
        assert "Dev Charter could not write charter/cards/CARD-001-order-page.md (Permission denied)." in said
        assert "Make sure you may write there" in said and "Traceback" not in said

        monkeypatch.setenv("CODEX_THREAD_ID", "019a-codex")
        said = several.run("card", "new", "Order page", ok=False).output
        assert ("A coding agent's sandbox lets it write only inside the folder it was started in: start it in the "
                f"product's root folder, {several.root}") in said
    finally:
        cards.chmod(0o755)


def test_git_hooks_the_system_refuses_leave_the_rest_of_sync_done(several: Product):
    hooks_dir = several.root / ".git/hooks"
    for name in ("pre-commit", "post-commit"):
        (hooks_dir / name).unlink()
        (several.root / "api/.git/hooks" / name).unlink()
    hooks_dir.chmod(0o555)
    try:
        said = several.run("sync").output
    finally:
        hooks_dir.chmod(0o755)
    assert "This folder: could not write its commit checks" in said
    assert "run `dev-charter sync` yourself in a terminal" in said
    assert "api: installed the pre-commit hook." in said, "the other repository was still done"


def test_guides_name_an_agent_only_in_a_section_about_the_agents():
    for path in sorted([*(GUIDES / "guides").glob("*.md"), *(GUIDES / "templates").glob("*.md")]):
        heading = ""
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if line.startswith("## "):
                heading = line
            if re.search(r"Claude Code|Codex", line) and not ("Claude Code" in heading and "Codex" in heading):
                pytest.fail(f"{path.name}:{number} names one agent where any agent is meant: {line.strip()}")
