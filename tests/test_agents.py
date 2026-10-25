# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
import pytest

from dev_charter import __version__, agents
from dev_charter.errors import CharterError


def test_the_block_is_created_when_there_is_no_agents_file(tmp_path):
    assert agents.write_block(tmp_path) == "created"
    text = (tmp_path / "AGENTS.md").read_text()
    assert text.startswith(f"<!-- dev-charter:start v{__version__} -->")
    assert "dev-charter guide <stage>" in text
    assert agents.block_state(tmp_path) == (agents.CURRENT, __version__)


def test_a_section_from_an_earlier_release_is_out_of_date(tmp_path):
    (tmp_path / "AGENTS.md").write_text("<!-- dev-charter:start v0.1 -->\nold rules\n<!-- dev-charter:end -->\n")
    assert agents.block_state(tmp_path, "0.1.2") == (agents.OLDER, "0.1")
    assert agents.write_block(tmp_path, "0.1.2") == "updated"
    assert agents.block_state(tmp_path, "0.1.2") == (agents.CURRENT, "0.1.2")


def test_a_hand_edit_inside_the_section_is_noticed(tmp_path):
    agents.write_block(tmp_path, "0.1.2")
    path = tmp_path / "AGENTS.md"
    path.write_text(path.read_text().replace("Never write an ID yourself.", "IDs are fine."))
    assert agents.block_state(tmp_path, "0.1.2")[0] == agents.EDITED


def test_an_older_release_never_rewrites_a_newer_section(tmp_path):
    agents.write_block(tmp_path, "0.1.3")
    before = (tmp_path / "AGENTS.md").read_text()
    assert agents.block_state(tmp_path, "0.1.2") == (agents.NEWER, "0.1.3")
    assert agents.write_block(tmp_path, "0.1.2") == agents.NEWER
    assert (tmp_path / "AGENTS.md").read_text() == before


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
