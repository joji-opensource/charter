# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Upgrading (0.2): a project set up for an older Dev Charter moves to the installed one with `sync --upgrade`, the
pin last so that running it again finishes the job; a project that needs a newer Dev Charter is never moved back."""

from dev_charter import ci, config

from .conftest import Product

OLDER = ">=0.0,<0.1"


def set_up_older(shop: Product) -> None:
    """A project whose pin and CI workflow were written by a Dev Charter older than the one installed."""
    shop.run("ci")
    workflow = shop.root / ci.WORKFLOW
    workflow.write_text(workflow.read_text().replace(config.version_range(), OLDER))
    config.write_pin(shop.root, OLDER)


def pin_line(shop: Product) -> str:
    return next(line for line in (shop.root / "charter.toml").read_text().splitlines()
                if line.startswith("dev-charter"))


def test_a_project_for_an_older_dev_charter_upgrades_in_one_command(git_product: Product):
    shop = git_product
    set_up_older(shop)
    refused = shop.run("check", ok=False).output
    assert f"Run `dev-charter sync --upgrade` to move it to {config.version_range()}" in refused

    said = shop.run("sync", "--upgrade").output
    assert f"{ci.WORKFLOW}: now installs Dev Charter {config.version_range()}." in said
    assert f"this project now works with Dev Charter {config.version_range()} (it said {OLDER})" in said
    assert "codex plugin marketplace upgrade" in said
    assert pin_line(shop).startswith(f'dev-charter = "{config.version_range()}"')
    assert pin_line(shop).endswith("# the Dev Charter versions this project works with"), "only the range changed"
    assert f'uv tool install "dev-charter{config.version_range()}"' in (shop.root / ci.WORKFLOW).read_text()
    shop.commit("after the upgrade")  # the commit check runs, and passes
    assert "this project now works" not in shop.run("sync", "--upgrade").output, "nothing left to move"


def test_a_failed_upgrade_is_finished_by_running_it_again(git_product: Product):
    shop = git_product
    set_up_older(shop)
    workflow = shop.root / ci.WORKFLOW
    workflow.chmod(0o444)
    try:
        said = shop.run("sync", "--upgrade", ok=False).output
    finally:
        workflow.chmod(0o644)
    assert f"Dev Charter could not write {ci.WORKFLOW}" in said and "Traceback" not in said
    assert OLDER in pin_line(shop), "the pin moves last, so it has not moved"
    shop.run("sync", "--upgrade")
    assert config.version_range() in pin_line(shop)


def test_a_project_that_needs_a_newer_dev_charter_is_never_moved_back(git_product: Product):
    shop = git_product
    config.write_pin(shop.root, ">=9.0,<9.1")
    said = shop.run("sync", "--upgrade", ok=False).output
    assert "This project uses Dev Charter >=9.0,<9.1, newer than the" in said
    assert ">=9.0,<9.1" in pin_line(shop)


def test_a_workflow_changed_by_hand_is_left_alone(git_product: Product):
    shop = git_product
    set_up_older(shop)
    workflow = shop.root / ci.WORKFLOW
    by_hand = workflow.read_text().replace(f'uv tool install "dev-charter{OLDER}"', "pipx install dev-charter")
    workflow.write_text(by_hand)
    said = shop.run("sync", "--upgrade").output
    assert f"{ci.WORKFLOW}: its install line is not the one `dev-charter ci` wrote, so it was left as it is" in said
    assert "pipx install dev-charter" in workflow.read_text()
