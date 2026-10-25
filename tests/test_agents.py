# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
import pytest

from dev_charter import agents
from dev_charter.errors import CharterError


def test_the_block_is_created_when_there_is_no_agents_file(tmp_path):
    assert agents.write_block(tmp_path) == "created"
    text = (tmp_path / "AGENTS.md").read_text()
    assert text.startswith(f"<!-- dev-charter:start v{agents.minor()} -->")
    assert "dev-charter guide <stage>" in text
    assert agents.block_version(tmp_path) == agents.minor()


def test_the_marker_carries_the_minor_version_only():
    assert agents.minor("0.1.2") == agents.minor("0.1.7") == "0.1"


def test_text_outside_the_block_is_never_touched(tmp_path):
    own = "# Our rules\n\nUse tabs, not spaces.\n"
    (tmp_path / "AGENTS.md").write_text(own)
    assert agents.write_block(tmp_path) == "updated"
    assert (tmp_path / "AGENTS.md").read_text().startswith(own + "\n<!-- dev-charter:start")
    assert agents.write_block(tmp_path) == "unchanged"


def test_an_old_block_is_replaced_in_place(tmp_path):
    (tmp_path / "AGENTS.md").write_text("before\n<!-- dev-charter:start v0.0.1 -->\nold rules\n"
                                        "<!-- dev-charter:end -->\nafter\n")
    assert agents.write_block(tmp_path) == "updated"
    text = (tmp_path / "AGENTS.md").read_text()
    assert text.startswith("before\n<!-- dev-charter:start") and text.endswith("<!-- dev-charter:end -->\nafter\n")
    assert "old rules" not in text


def test_two_blocks_are_refused(tmp_path):
    block = "<!-- dev-charter:start v0.0.1 -->\nx\n<!-- dev-charter:end -->\n"
    (tmp_path / "AGENTS.md").write_text(block + block)
    with pytest.raises(CharterError, match="2 Dev Charter blocks"):
        agents.write_block(tmp_path)


def test_the_block_stays_short():
    assert len(agents.render_block().splitlines()) <= 40
