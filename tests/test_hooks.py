# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
import os
import subprocess
from pathlib import Path

import pytest

from dev_charter import config, hooks

from .conftest import FEATURE_F014, Product

FEATURE = FEATURE_F014.replace("decisions: [DEC-001]", "decisions: []")


def hook(product: Product, name: str) -> Path:
    return product.root / ".git" / "hooks" / name


def test_init_installs_both_hooks_and_sync_leaves_them_alone(git_product: Product):
    for name in ("pre-commit", "post-commit"):
        path = hook(git_product, name)
        assert hooks.MARKER in path.read_text() and os.access(path, os.X_OK)
    before = hook(git_product, "pre-commit").read_text()
    assert "installed" not in git_product.run("sync").output
    assert hook(git_product, "pre-commit").read_text() == before


def test_a_hook_that_is_not_ours_is_never_overwritten(git_product: Product):
    path = hook(git_product, "pre-commit")
    path.write_text("#!/bin/sh\necho team lint\n")
    output = git_product.run("sync").output
    assert "already has a pre-commit hook, left as it is" in output and "check --staged" in output
    assert path.read_text() == "#!/bin/sh\necho team lint\n"
    assert "Commits to shop are not checked" in git_product.run("check").output


def test_light_mode_checks_in_ci_only(git_product: Product):
    toml = git_product.root / "charter.toml"
    toml.write_text(toml.read_text().replace('mode = "standard"', 'mode = "light"'))
    assert "removed the pre-commit check" in git_product.run("sync").output
    assert not hook(git_product, "pre-commit").exists() and hook(git_product, "post-commit").exists()


def test_a_folder_inside_a_bigger_repository_gets_no_hooks(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    demo = tmp_path / "examples" / "demo"
    demo.mkdir(parents=True)
    notes = Product(demo).run("init", "--yes").output
    assert "not the top of one, so no commit checks were installed" in notes
    assert not (tmp_path / ".git" / "hooks" / "pre-commit").exists()
    assert hooks.missing_checks(config.load(demo)) == []


def test_check_staged_stops_a_new_untagged_file(git_product: Product, monkeypatch: pytest.MonkeyPatch):
    git_product.write("charter/features/F-014-track-my-order.md", FEATURE)
    git_product.commit("feature")
    git_product.write("shop/orders/status.py", "def step(order):\n    return order['step']\n")
    git_product.git("add", "shop/orders/status.py")
    monkeypatch.chdir(git_product.root)
    result = git_product.run("check", "--staged", ok=False)
    assert result.exit_code == 1
    assert "This new code file does not say which feature it serves" in result.output
    assert "The commit was stopped" in result.output

    git_product.write("shop/orders/status.py", "# serves: F-014\ndef step(order):\n    return order['step']\n")
    git_product.git("add", "shop/orders/status.py")
    assert git_product.run("check", "--staged").exit_code == 0


def test_a_real_commit_is_stopped_and_then_rebuilds_the_ledger(git_product: Product):
    git_product.write("charter/features/F-014-track-my-order.md", FEATURE)
    git_product.commit("feature")
    git_product.write("shop/orders/status.py", "def step(order):\n    return order['step']\n")
    git_product.git("add", "shop/orders/status.py")
    refused = git_product.git("commit", "-m", "order status", check=False)
    assert refused.returncode != 0
    assert "does not say which feature it serves" in refused.stdout + refused.stderr

    git_product.write("shop/orders/status.py", "# serves: F-014\ndef step(order):\n    return order['step']\n")
    git_product.git("add", "shop/orders/status.py")
    (git_product.root / "LEDGER.xlsx").unlink(missing_ok=True)
    git_product.git("commit", "-m", "order status")
    assert (git_product.root / "LEDGER.xlsx").exists()
