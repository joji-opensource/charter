# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""Reading and writing the files in charter/, and handing out IDs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from importlib.resources import files
from pathlib import Path

import yaml

from . import git
from .config import CHARTER_DIR, Config
from .errors import CharterError, FileProblem
from .model import (
    CARD,
    CARD_STATES,
    DECISION,
    FEATURE,
    PRIORITIES,
    PROMISE,
    STATES,
    Card,
    Criterion,
    Decision,
    Entry,
    Idea,
    Kind,
    SignOff,
)

IDEAS_FILE = "ideas.md"
LEGACY_HANDOFF_FILE = "handoff.md"  # one handoff per product, before handoffs moved into cards

LABEL_RE = re.compile(r"^\*\*(?P<label>[^*]+?)\*\*\s*(?P<text>.*)$")
CRITERION_RE = re.compile(r"^-\s+\*\*(?P<letter>[a-z])\.\*\*\s*(?P<text>.*)$")
PLACEHOLDER_RE = re.compile(r"<[^<>\n]{2,}>")
CRITERION_REF_RE = re.compile(r"^[FP]-\d{3,}(\.[a-z])?$")
DECISION_ID_RE = re.compile(r"^DEC-\d{3,}$")
SECTIONS = {
    "feature": ("Done means", "Sign-offs"),
    "promise": ("Done means", "Sign-offs"),
    "decision": (),
    "card": None,  # a card's sections are free-form
}


@dataclass
class Parsed:
    path: Path
    meta: dict
    meta_lines: dict[str, int]
    labels: dict[str, tuple[str, int]]
    sections: dict[str, list[tuple[int, str]]]
    section_lines: dict[str, int]
    body_line: int  # the first line after the details


@dataclass
class Project:
    config: Config
    features: list[Entry] = field(default_factory=list)
    promises: list[Entry] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    cards: list[Card] = field(default_factory=list)
    ideas: list[Idea] = field(default_factory=list)
    problems: list[FileProblem] = field(default_factory=list)

    @property
    def entries(self) -> list[Entry]:
        return self.features + self.promises

    def ids(self) -> set[str]:
        return {e.id for e in self.entries} | {d.id for d in self.decisions} | {c.id for c in self.cards}


# --- parsing ---------------------------------------------------------------------------------------------------------


def parse(path: Path, kind: Kind, text: str | None = None) -> Parsed:
    """Split a charter file into its details block, labelled story and sections.

    `text` is the file's content when it comes from somewhere other than the disk, such as another branch.
    """
    lines = (path.read_text(encoding="utf-8") if text is None else text).splitlines()
    if not lines or lines[0].strip() != "---":
        raise FileProblem(
            path, 1, "The file must start with a line of three dashes (---), then the details (id, title, …), "
            "then another line of three dashes."
        )
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise FileProblem(path, 1, "The details at the top never end: add a line of three dashes (---) after them.")
    try:
        meta = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        problem = getattr(exc, "problem", None) or "it is not in the form 'name: value'"
        raise FileProblem(path, mark.line + 2 if mark else 2, f"The details could not be read: {problem}.") from exc
    if not isinstance(meta, dict):
        raise FileProblem(path, 2, "The details at the top must be lines of the form 'name: value'.")
    meta_lines = {}
    for i in range(1, end):
        match = re.match(r"^([A-Za-z_][\w-]*)\s*:", lines[i])
        if match:
            meta_lines.setdefault(match.group(1), i + 1)

    allowed_sections = SECTIONS[kind.name]
    labels: dict[str, tuple[str, int]] = {}
    sections: dict[str, list[tuple[int, str]]] = {}
    section_lines: dict[str, int] = {}
    current_label: str | None = None
    current_section: str | None = None
    in_comment = False
    for index in range(end + 1, len(lines)):
        number = index + 1
        raw = lines[index]
        stripped = raw.strip()
        if in_comment:
            in_comment = "-->" not in stripped
            continue
        if stripped.startswith("<!--"):
            in_comment = "-->" not in stripped
            continue
        if stripped.startswith("## "):
            heading = stripped[3:].strip()
            if allowed_sections is not None and heading not in allowed_sections:
                expected = ", ".join(f"'## {s}'" for s in allowed_sections) or "none"
                raise FileProblem(path, number, f"A {kind.name} has no section '## {heading}'. Its sections are: "
                                  f"{expected}.")
            if heading in sections:
                raise FileProblem(path, number, f"The section '## {heading}' appears twice.")
            sections[heading] = []
            section_lines[heading] = number
            current_section, current_label = heading, None
            continue
        if current_section is not None:
            sections[current_section].append((number, raw))
            continue
        if not stripped:
            current_label = None
            continue
        match = LABEL_RE.match(stripped)
        if match:
            label = match.group("label").strip().rstrip(":").strip()
            if label not in kind.labels:
                raise FileProblem(path, number, f"'**{label}**' is not a label a {kind.name} uses. "
                                  f"Its labels are: {_label_list(kind)}.")
            if label in labels:
                raise FileProblem(path, number, f"'**{label}**' appears twice.")
            labels[label] = (match.group("text").strip().lstrip(":").strip(), number)
            current_label = label
        elif current_label is not None:
            text, first_line = labels[current_label]
            labels[current_label] = (f"{text} {stripped}".strip(), first_line)
        else:
            raise FileProblem(path, number, f"This line does not belong to a label. Start it with one of "
                              f"{_label_list(kind)}, or join it to the line above.")
    return Parsed(path, meta, meta_lines, labels, sections, section_lines, body_line=end + 2)


def _label_list(kind: Kind) -> str:
    return ", ".join(f"**{label}**" for label in kind.labels)


def _meta_line(parsed: Parsed, key: str) -> int:
    return parsed.meta_lines.get(key, 2)


def _require_id(parsed: Parsed, kind: Kind) -> str:
    value = parsed.meta.get("id")
    if not value:
        raise FileProblem(parsed.path, 2, f"The details need an id, for example 'id: {kind.format_id(1)}'.")
    value = str(value)
    if not re.fullmatch(rf"{kind.prefix}-\d{{3,}}", value):
        raise FileProblem(parsed.path, _meta_line(parsed, "id"),
                          f"'{value}' is not a {kind.name} ID; they look like {kind.format_id(14)}.")
    if not (parsed.path.name == f"{value}.md" or parsed.path.name.startswith(f"{value}-")):
        raise FileProblem(parsed.path, _meta_line(parsed, "id"),
                          f"The id is {value} but the file name does not start with it. Rename the file to start "
                          f"with '{value}-'.")
    return value


def _require_text(parsed: Parsed, key: str) -> str:
    value = parsed.meta.get(key)
    if value is None or not str(value).strip():
        raise FileProblem(parsed.path, _meta_line(parsed, key), f"The details need a {key}.")
    return str(value).strip()


def _list_of(parsed: Parsed, key: str, pattern: re.Pattern, example: str) -> list[str]:
    value = parsed.meta.get(key) or []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise FileProblem(parsed.path, _meta_line(parsed, key), f"'{key}' must be a list, for example [{example}].")
    items = [str(v) for v in value]
    for item in items:
        if not pattern.fullmatch(item):
            raise FileProblem(parsed.path, _meta_line(parsed, key),
                              f"'{item}' in '{key}' is not an ID like {example}.")
    return items


def _require_labels(parsed: Parsed, kind: Kind) -> None:
    for label in kind.required_labels:
        if label not in parsed.labels:
            raise FileProblem(parsed.path, parsed.body_line, f"The **{label}** line is missing.")


def _criteria(parsed: Parsed) -> list[Criterion]:
    if "Done means" not in parsed.sections:
        raise FileProblem(parsed.path, parsed.body_line,
                          "The '## Done means' section is missing: list what a person or a test can check.")
    criteria: list[Criterion] = []
    for number, raw in parsed.sections["Done means"]:
        stripped = raw.strip()
        if not stripped:
            continue
        match = CRITERION_RE.match(stripped)
        if match:
            letter = match.group("letter")
            if any(c.letter == letter for c in criteria):
                raise FileProblem(parsed.path, number, f"Check '{letter}.' appears twice under Done means.")
            criteria.append(Criterion(letter, match.group("text").strip(), number))
        elif raw[:1] in (" ", "\t") and criteria:
            last = criteria[-1]
            criteria[-1] = Criterion(last.letter, f"{last.text} {stripped}", last.line)
        else:
            raise FileProblem(parsed.path, number,
                              "Each line under Done means must look like: - **a.** something a person or a test "
                              "can check.")
    return criteria


def _signoffs(parsed: Parsed, criteria: list[Criterion]) -> list[SignOff]:
    letters = {c.letter for c in criteria}
    signoffs: list[SignOff] = []
    for number, raw in parsed.sections.get("Sign-offs", []):
        stripped = raw.strip()
        if not stripped:
            continue
        if not stripped.startswith("- "):
            raise FileProblem(parsed.path, number,
                              "Each sign-off must look like: - 2026-10-24 · b · Name · what they saw")
        parts = [p.strip() for p in stripped[2:].split("·", 3)]
        if len(parts) != 4 or not all(parts):
            raise FileProblem(parsed.path, number,
                              "A sign-off has four parts separated by '·': date · check letter or 'proven' · name · "
                              "what they saw.")
        try:
            on = date.fromisoformat(parts[0])
        except ValueError as exc:
            raise FileProblem(parsed.path, number, f"'{parts[0]}' is not a date like 2026-10-24.") from exc
        what = parts[1]
        if what != "proven" and what not in letters:
            raise FileProblem(parsed.path, number,
                              f"'{what}' is neither 'proven' nor one of the checks under Done means "
                              f"({', '.join(sorted(letters)) or 'none yet'}).")
        signoffs.append(SignOff(on, what, parts[2], parts[3], number))
    return signoffs


def _placeholders(parsed: Parsed, criteria: list[Criterion]) -> list[tuple[int, str]]:
    found = []
    for key in ("title", "area", "release"):
        value = parsed.meta.get(key)
        if isinstance(value, str) and PLACEHOLDER_RE.search(value):
            found.append((_meta_line(parsed, key), key))
    for label, (text, line) in parsed.labels.items():
        if PLACEHOLDER_RE.search(text):
            found.append((line, label))
    for criterion in criteria:
        if PLACEHOLDER_RE.search(criterion.text):
            found.append((criterion.line, f"Done means {criterion.letter}."))
    return found


def read_entry(path: Path, kind: Kind, text: str | None = None) -> Entry:
    parsed = parse(path, kind, text)
    entry_id = _require_id(parsed, kind)
    title = _require_text(parsed, "title")
    state = str(parsed.meta.get("state") or "")
    if state not in STATES:
        raise FileProblem(path, _meta_line(parsed, "state"),
                          f"state is '{state}'; it must be one of {', '.join(STATES)}.")
    priority = parsed.meta.get("priority")
    if priority and str(priority) not in PRIORITIES:
        raise FileProblem(path, _meta_line(parsed, "priority"),
                          f"priority is '{priority}'; it must be one of {', '.join(PRIORITIES)}.")
    _list_of(parsed, "decisions", DECISION_ID_RE, "DEC-001")
    _require_labels(parsed, kind)
    criteria = _criteria(parsed)
    signoffs = _signoffs(parsed, criteria)
    story = {label: text for label, (text, _) in parsed.labels.items()}
    words = sum(len(t.split()) for t in story.values()) + sum(len(c.text.split()) for c in criteria)
    return Entry(
        kind=kind,
        id=entry_id,
        title=title,
        state=state,
        path=path,
        meta=parsed.meta,
        story=story,
        criteria=criteria,
        signoffs=signoffs,
        words=words,
        placeholders=_placeholders(parsed, criteria),
    )


def read_decision(path: Path, text: str | None = None) -> Decision:
    parsed = parse(path, DECISION, text)
    decision_id = _require_id(parsed, DECISION)
    title = _require_text(parsed, "title")
    _require_labels(parsed, DECISION)
    raw_date = parsed.meta.get("date")
    on = None
    if raw_date:
        try:
            on = raw_date if isinstance(raw_date, date) else date.fromisoformat(str(raw_date))
        except ValueError as exc:
            raise FileProblem(path, _meta_line(parsed, "date"), f"'{raw_date}' is not a date like 2026-10-24.") from exc
    return Decision(
        id=decision_id,
        title=title,
        path=path,
        on=on,
        decided_by=str(parsed.meta.get("decided_by") or ""),
        features=_list_of(parsed, "features", CRITERION_REF_RE, "F-014"),
        decision=parsed.labels["Decision"][0],
        instead_of=parsed.labels.get("Instead of", ("", 0))[0],
        because=parsed.labels["Because"][0],
    )


def _section_lines(parsed: Parsed, heading: str) -> list[str]:
    return [raw.strip() for _, raw in parsed.sections.get(heading, [])
            if raw.strip() and not raw.strip().startswith("<!--")]


def _next_step(parsed: Parsed) -> str:
    for line in _section_lines(parsed, "Handoff"):
        label, _, text = line.lstrip("-").strip().partition(":")
        if label.strip().lower() == "next step" and text.strip():
            return text.strip()
    return ""


def read_card(path: Path, text: str | None = None) -> Card:
    parsed = parse(path, CARD, text)
    card_id = _require_id(parsed, CARD)
    title = _require_text(parsed, "title")
    state = str(parsed.meta.get("state") or "open")
    if state not in CARD_STATES:
        raise FileProblem(path, _meta_line(parsed, "state"),
                          f"state is '{state}'; a card is {' or '.join(CARD_STATES)}.")
    _require_labels(parsed, CARD)
    return Card(
        id=card_id,
        title=title,
        path=path,
        state=state,
        serves=_list_of(parsed, "serves", CRITERION_REF_RE, "F-014.a"),
        goal=parsed.labels["Goal"][0],
        next_step=_next_step(parsed),
        allowed=tuple(line.lstrip("-").strip().strip("`") for line in _section_lines(parsed, "Allowed paths")),
    )


def read_ideas(path: Path) -> list[Idea]:
    ideas = []
    if not path.is_file():
        return ideas
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()
        if not stripped.startswith("- "):
            continue
        parts = [p.strip() for p in stripped[2:].split("·")]
        on = None
        try:
            on = date.fromisoformat(parts[0])
            parts = parts[1:]
        except ValueError:
            pass
        source = ""
        if len(parts) > 1 and parts[-1].lower().startswith("from "):
            source = parts.pop()[5:].strip()
        ideas.append(Idea(on, " · ".join(parts), source, number))
    return ideas


def load_project(config: Config) -> Project:
    """Read every charter file; problems are collected, not raised, so one bad file never hides the rest."""
    folder = config.charter_dir
    if not folder.is_dir():
        raise CharterError(f"There is no {folder.name}/ folder in {config.root}. Run `dev-charter init` to create it.")
    project = Project(config)
    readers = (
        (FEATURE, lambda p: read_entry(p, FEATURE), project.features),
        (PROMISE, lambda p: read_entry(p, PROMISE), project.promises),
        (DECISION, read_decision, project.decisions),
        (CARD, read_card, project.cards),
    )
    for kind, reader, target in readers:
        for path in sorted((folder / kind.folder).glob("*.md")):
            try:
                target.append(reader(path))
            except FileProblem as problem:
                project.problems.append(problem)
    project.ideas = read_ideas(folder / IDEAS_FILE)
    return project


# --- writing ---------------------------------------------------------------------------------------------------------


def template(name: str) -> str:
    return files("dev_charter.templates").joinpath(name).read_text(encoding="utf-8")


def slug(title: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return text[:48].rstrip("-") or "untitled"


def used_ids(config: Config, kind: Kind) -> set[int]:
    """Every number this kind has used: on disk, and on any branch in git's history, deleted ones included."""
    names = {path.name for path in (config.charter_dir / kind.folder).glob(f"{kind.prefix}-*.md")}
    names |= git.names_in_history(config.root, f"{CHARTER_DIR}/{kind.folder}")
    return {int(match.group(1)) for name in names if (match := re.match(rf"^{kind.prefix}-(\d+)", name))}


def next_id(config: Config, kind: Kind) -> str:
    """The next ID after every one ever used, so an ID is never given out twice, even across branches."""
    return kind.format_id(max(used_ids(config, kind), default=0) + 1)


def create(config: Config, kind: Kind, title: str, values: dict[str, str] | None = None) -> tuple[str, Path]:
    """Write a new file from the kind's template with the next free ID. Returns the ID and the path."""
    title = " ".join(title.split())
    if not title:
        raise CharterError(f"A {kind.name} needs a title.")
    folder = config.charter_dir / kind.folder
    folder.mkdir(parents=True, exist_ok=True)
    new_id = next_id(config, kind)
    path = folder / f"{new_id}-{slug(title)}.md"
    text = template(f"{kind.name}.md")
    fields = {"id": new_id, "title": json.dumps(title), "date": date.today().isoformat(), **(values or {})}
    for key, value in fields.items():
        text = text.replace("{{" + key + "}}", value)
    path.write_text(text, encoding="utf-8")
    return new_id, path


def park(config: Config, idea: str, source: str) -> Path:
    path = config.charter_dir / IDEAS_FILE
    if not path.exists():
        path.write_text(template(IDEAS_FILE), encoding="utf-8")
    idea = " ".join(idea.replace("·", "-").split())
    if not idea:
        raise CharterError("An idea needs some words.")
    line = f"- {date.today().isoformat()} · {idea}"
    if source.strip():
        line += f" · from {' '.join(source.replace('·', '-').split())}"
    text = path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + line + "\n", encoding="utf-8")
    return path
