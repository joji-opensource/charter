# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
import pytest

from dev_charter import config, store
from dev_charter.errors import FileProblem
from dev_charter.model import FEATURE

from .conftest import FEATURE_F014


def test_a_full_feature_reads_back_without_loss(tmp_path):
    path = tmp_path / "F-014-track-my-order.md"
    path.write_text(FEATURE_F014)
    entry = store.read_entry(path, FEATURE)
    assert (entry.id, entry.title, entry.state, entry.area, entry.priority, entry.release) == (
        "F-014", "Track my order", "agreed", "Orders and delivery", "Must", "Spring launch")
    assert entry.decisions == ["DEC-001"]
    assert entry.story["With"] == ("the current step (packed, shipped, out for delivery), the expected delivery date, "
                                   "and a text message when it is out for delivery")
    assert entry.story["Must also"] == "load in under 2 seconds on a phone · show me only my own orders"
    assert [c.letter for c in entry.criteria] == ["a", "b", "c"]
    assert [(s.what, s.person) for s in entry.signoffs] == [("b", "Joji John")]
    assert entry.placeholders == []


def test_a_label_written_with_a_colon_is_still_read(tmp_path):
    path = tmp_path / "F-014-x.md"
    path.write_text(FEATURE_F014.replace("**As a** customer", "**As a:** customer"))
    assert store.read_entry(path, FEATURE).story["As a"] == "customer of an online store"


@pytest.mark.parametrize(
    ("change", "line", "words"),
    [
        (lambda t: t.replace("---\nid", "id", 1), 1, "three dashes"),
        (lambda t: t.replace("state: agreed", "state: finished"), 7, "must be one of"),
        (lambda t: t.replace("priority: Must", "priority: Urgent"), 5, "must be one of"),
        (lambda t: t.replace("**So that**", "**Outcome**"), 16, "not a label"),
        (lambda t: t.replace("- **b.** A text", "- b. A text"), 21, "must look like"),
        (lambda t: t.replace("2026-10-24 · b", "24 Oct · b"), 26, "is not a date"),
        (lambda t: t.replace("2026-10-24 · b", "2026-10-24 · z"), 26, "neither 'proven'"),
        (lambda t: t.replace("id: F-014", "id: F-015"), 2, "file name does not start"),
        (lambda t: t.replace("## Done means", "## Notes"), 18, "has no section"),
    ],
)
def test_a_malformed_feature_names_the_file_and_line(tmp_path, change, line, words):
    path = tmp_path / "F-014-track-my-order.md"
    path.write_text(change(FEATURE_F014))
    with pytest.raises(FileProblem) as problem:
        store.read_entry(path, FEATURE)
    assert problem.value.line == line
    assert words in problem.value.message


def test_template_text_is_found(tmp_path):
    path = tmp_path / "F-014-x.md"
    path.write_text(FEATURE_F014.replace("**I want to** see", "**I want to** <what they want> see"))
    assert store.read_entry(path, FEATURE).placeholders == [(12, "I want to")]


def test_ids_continue_after_the_highest_even_with_gaps(product):
    cfg = config.load(product.root)
    product.write("charter/features/F-003-a.md", "x")
    product.write("charter/features/F-011-b.md", "x")
    assert store.next_id(cfg, FEATURE) == "F-012"


def test_a_new_feature_is_the_full_template_and_reads_back(product):
    cfg = config.load(product.root)
    new_id, path = store.create(cfg, FEATURE, "Pay with a saved card: one tap", {"area": '"Checkout"',
                                                                              "priority": '"Must"'})
    assert (new_id, path.name) == ("F-001", "F-001-pay-with-a-saved-card-one-tap.md")
    entry = store.read_entry(path, FEATURE)
    assert (entry.title, entry.state, entry.area, entry.priority) == (
        "Pay with a saved card: one tap", "idea", "Checkout", "Must")
    assert {where for _, where in entry.placeholders} >= {"As a", "I want to", "So that", "Done means a."}


def test_one_bad_file_never_hides_the_others(product):
    product.write("charter/features/F-014-track-my-order.md", FEATURE_F014)
    product.write("charter/features/F-015-broken.md", "no details here\n")
    project = store.load_project(config.load(product.root))
    assert [f.id for f in project.features] == ["F-014"]
    assert [p.path.name for p in project.problems] == ["F-015-broken.md"]


def test_ideas_are_parked_with_their_date_and_source(product):
    cfg = config.load(product.root)
    store.park(cfg, "Show the courier · on a map", "F-014")
    ideas = store.read_ideas(cfg.charter_dir / store.IDEAS_FILE)
    assert [(i.text, i.source) for i in ideas] == [("Show the courier - on a map", "F-014")]
    assert ideas[0].on is not None


def test_a_detail_written_twice_is_a_problem(tmp_path):
    path = tmp_path / "F-014-track-my-order.md"
    path.write_text(FEATURE_F014.replace("state: agreed\n", 'state: agreed\n"state": live\n'))
    with pytest.raises(FileProblem, match="'state' is written twice"):
        store.read_entry(path, FEATURE)
