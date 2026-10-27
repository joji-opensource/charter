# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The `dev-charter` command: a thin layer over the modules, speaking plain English."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import click

from . import (
    __version__,
    agents,
    check,
    ci,
    config,
    git,
    guides,
    hooks,
    notes,
    owner_review,
    pr,
    publish,
    remind,
    renumber,
    store,
    wip,
)
from . import guard as guard_module
from . import trace as trace_module
from .errors import REFUSED, CharterError, refused_write
from .model import CARD, DECISION, FEATURE, PRIORITIES, PROMISE, Kind
from .report import GENERATED, LEDGER_FILE, kept_message, take_snapshot, write_reports
from .status import ORDER

ID_REF_RE = re.compile(r"^[FP]-\d{3,}(\.[a-z])?$")


class Command(click.Group):
    """Shows a CharterError, or a write the system refused, in plain words instead of a traceback."""

    def invoke(self, ctx: click.Context):
        try:
            return super().invoke(ctx)
        except CharterError as exc:
            raise click.ClickException(str(exc)) from exc
        except OSError as exc:
            if exc.errno not in REFUSED or not exc.filename:
                raise
            try:
                root = config.find_root((ctx.obj or {}).get("start") or Path.cwd())
            except CharterError:
                root = None
            said = refused_write(Path(exc.filename), exc.strerror or str(exc), root, notes.run_by_an_agent())
            raise click.ClickException(said) from exc


def _open(ctx: click.Context) -> config.Config:
    root = config.find_root(ctx.obj["start"])
    cfg = config.load(root)
    config.check_version(cfg)
    return cfg


def _shown(cfg: config.Config, path: Path) -> str:
    try:
        return path.relative_to(cfg.root).as_posix()
    except ValueError:
        return str(path)


@click.group(cls=Command)
@click.version_option(package_name="dev-charter", prog_name="Dev Charter")
@click.option("--root", type=click.Path(file_okay=False, path_type=Path), default=None,
              help="The product's root folder (where charter.toml is). Defaults to this folder or the nearest above.")
@click.pass_context
def main(ctx: click.Context, root: Path | None) -> None:
    """Dev Charter: know what your product does, which code delivers it, and what is proven."""
    ctx.ensure_object(dict)
    ctx.obj["start"] = (root or Path.cwd()).resolve()


# --- setting up -------------------------------------------------------------------------------------------------------


@main.command()
@click.option("--name", help="The product's name. Defaults to the folder's name.")
@click.option("--mode", type=click.Choice(config.MODES), help="How strict to be. Defaults to standard.")
@click.option("--repo", "repos", multiple=True, help="A repository folder, relative to this one. Repeat for each. "
              "Defaults to this folder.")
@click.option("--area", "areas", multiple=True, help="A product area, such as 'Checkout'. Repeat for each.")
@click.option("--role", "roles", multiple=True, help="A kind of user, such as 'customer'. Repeat for each.")
@click.option("--integration-branch", default="", help="The branch work is merged into. Defaults to the remote's "
              "default branch.")
@click.option("--owner", default="", help="The GitHub name (@name) whose approval a pull request needs to change "
              "features, promises or decisions.")
@click.option("--yes", is_flag=True, help="Use the defaults for anything not given; ask nothing.")
@click.pass_context
def init(ctx: click.Context, name, mode, repos, areas, roles, integration_branch, owner, yes) -> None:
    """Set up Dev Charter in this product. Safe to run again: it only adds what is missing."""
    root: Path = ctx.obj["start"]
    if not root.is_dir():
        raise CharterError(f"{root} is not a folder.")
    for parent in root.parents:
        if (parent / config.CONFIG_FILE).is_file():
            raise CharterError(f"This folder is inside another Dev Charter product at {parent}. Run init there, or "
                               "add this folder to that product's charter.toml as a repository.")
    done: list[str] = []
    config_path = root / config.CONFIG_FILE
    if config_path.exists():
        done.append(f"{config.CONFIG_FILE} already there; left as it is")
    else:
        ask = not yes and sys.stdin.isatty()
        if ask:
            name = name or click.prompt("Product name", default=root.name)
            if not areas:
                areas = _split(click.prompt("Product areas, separated by commas (for example: Checkout, Accounts)",
                                            default="", show_default=False))
            if not roles:
                roles = _split(click.prompt("Kinds of users, separated by commas (for example: customer, admin)",
                                            default="", show_default=False))
            mode = mode or click.prompt("How strict to be", type=click.Choice(config.MODES), default="standard")
        repos = list(repos) or ["."]
        for repo in repos:
            if not (root / repo).is_dir():
                raise CharterError(f"The repository folder '{repo}' does not exist under {root}.")
        config_path.write_text(
            config.render(name or root.name, mode or "standard", repos, list(roles), list(areas),
                          integration_branch=integration_branch), encoding="utf-8"
        )
        done.append(f"created {config.CONFIG_FILE}")

    charter_dir = root / config.CHARTER_DIR
    for kind in (FEATURE, PROMISE, DECISION, CARD):
        folder = charter_dir / kind.folder
        if not folder.is_dir():
            folder.mkdir(parents=True)
            (folder / ".gitkeep").touch()
            done.append(f"created {config.CHARTER_DIR}/{kind.folder}/")
    ideas = charter_dir / store.IDEAS_FILE
    if not ideas.exists():
        ideas.write_text(store.template(store.IDEAS_FILE), encoding="utf-8")
        done.append(f"created {config.CHARTER_DIR}/{store.IDEAS_FILE}")

    outcome = agents.write_block(root)
    if outcome == agents.NEWER:
        done.append(f"left the Dev Charter section of {agents.AGENTS_FILE} as it is: a newer Dev Charter wrote it "
                    "(upgrade with `uv tool upgrade dev-charter`)")
    elif outcome != "unchanged":
        done.append(f"{outcome} the Dev Charter section of {agents.AGENTS_FILE}")
    cfg = config.load(root)
    done += agents.write_pointers(cfg)
    done += _git_files(root)
    if owner:
        done.append(_codeowners(root, owner))
    done += hooks.install(cfg)

    click.echo(f"Dev Charter is set up in {root}.")
    for line in done:
        click.echo(f"  - {line}")
    click.echo('Next: add your first feature with `dev-charter feature new "<title>"`, or ask your coding agent to.')


def _git_files(root: Path) -> list[str]:
    """Keep the generated files out of git, and let the files every branch adds to merge line by line."""
    done = []
    ignored = (
        ([f"/{name}" for name in GENERATED] + [f"/{config.LOCAL_DIR}/"],
         "# Dev Charter: generated views, and this clone's own settings"),
        ([f"/~${LEDGER_FILE}"], f"# Dev Charter: the lock file Excel keeps while {LEDGER_FILE} is open"),
    )
    if any([_add_lines(root / ".gitignore", lines, comment) for lines, comment in ignored]):
        done.append("added Dev Charter's lines to .gitignore")
    merged = (
        ([store.IDEAS_FILE], "# Dev Charter: ideas parked on different branches merge line by line"),
        ([owner_review.NOTES_FILE, owner_review.LOG_FILE],
         "# Dev Charter: review notes and the review log merge line by line"),
    )
    for names, comment in merged:
        if _add_lines(root / ".gitattributes", [f"{config.CHARTER_DIR}/{name} merge=union" for name in names],
                      comment):
            done.append(f"made {' and '.join(names)} merge line by line across branches (.gitattributes)")
    return done


def _split(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _add_lines(path: Path, lines: list[str], comment: str) -> bool:
    """Add the lines a file lacks, under a comment, leaving everything already there alone."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    present = {line.strip() for line in text.splitlines()}
    missing = [line for line in lines if line not in present]
    if not missing:
        return False
    prefix = text if not text or text.endswith("\n") else text + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prefix + ("\n" if prefix else "") + comment + "\n" + "".join(f"{line}\n" for line in missing),
                    encoding="utf-8")
    return True


def _codeowners(root: Path, owner: str) -> str:
    if git.toplevel(root) != root.resolve():
        return "no CODEOWNERS written: this folder is inside a bigger git repository."
    owner = owner if owner.startswith("@") else f"@{owner}"
    lines = [f"/{config.CHARTER_DIR}/{kind.folder}/ {owner}" for kind in (FEATURE, PROMISE, DECISION)]
    _add_lines(root / ".github" / "CODEOWNERS", lines,
               "# Dev Charter: product changes need the product owner's approval")
    return (f"pull requests that change features, promises or decisions now need {owner}'s approval once GitHub's "
            "'Require review from Code Owners' is turned on for the integration branch")


@main.command(name="ci")
@click.pass_context
def ci_command(ctx: click.Context) -> None:
    """Write the GitHub workflow that checks each pull request and keeps the team's ledger on the `ledger` branch."""
    cfg = _open(ctx)
    path, outcome = ci.write(cfg)
    click.echo(f"{_shown(cfg, path)}: {outcome}. Commit it; then pull requests get a plain-English summary and checks, "
               "and the `ledger` branch holds the team's LEDGER.xlsx after each merge.")
    if not any(repo.results for repo in cfg.repos):
        click.echo('Set `results = ["reports/*.xml"]` in charter.toml so statuses include the tests the workflow runs.')


@main.command()
@click.option("--upgrade", is_flag=True, help="Move this project to the installed Dev Charter's versions as well.")
@click.pass_context
def sync(ctx: click.Context, upgrade: bool) -> None:
    """Refresh what Dev Charter manages (the AGENTS.md section and its pointers, the git hooks, and its lines in
    .gitignore and .gitattributes) after an upgrade or a change of mode. With --upgrade, also move the project to the
    installed Dev Charter's versions: the pin in charter.toml, changed last so that running it again finishes the job,
    and the install line of the workflow `dev-charter ci` wrote."""
    if not upgrade:
        cfg = _open(ctx)
    else:
        cfg = config.load(config.find_root(ctx.obj["start"]))
        if not config.pin_is_behind(cfg):
            config.check_version(cfg)  # a project that needs a newer Dev Charter is never moved back
    outcome = agents.write_block(cfg.root)
    if outcome == agents.NEWER:
        click.echo(f"{agents.AGENTS_FILE}: left as it is; a newer Dev Charter wrote its section. Upgrade with "
                   "`uv tool upgrade dev-charter`.")
    else:
        click.echo(f"{agents.AGENTS_FILE}: {outcome}.")
    for note in agents.write_pointers(cfg) + _git_files(cfg.root) + hooks.install(cfg):
        click.echo(note)
    if not upgrade:
        return
    versions = config.version_range()
    if note := ci.upgrade_install(cfg, versions):
        click.echo(note)
    if cfg.versions and config.write_pin(cfg.root, versions):
        click.echo(f"{config.CONFIG_FILE}: this project now works with Dev Charter {versions} "
                   f"(it said {cfg.versions}).")
    click.echo("Then update the Dev Charter plugin in each coding agent: in Claude Code, from /plugin; in Codex, run "
               "`codex plugin marketplace upgrade`, then trust its changed hooks in /hooks.")


# --- adding to the charter -------------------------------------------------------------------------------------------


def _created(cfg: config.Config, kind: Kind, new_id: str, path: Path) -> None:
    click.echo(f"Created {new_id} in {_shown(cfg, path)}.")
    click.echo(f"Fill in every line marked <…>, following `dev-charter guide {_guide_for(kind)}`.")
    fetched = git.last_fetch(cfg.root)
    if git.has_remote(cfg.root) and (fetched is None or time.time() - fetched > 86400):
        click.echo(f"This clone has not fetched in over a day, so a teammate may already have used {new_id}. Run "
                   f"`git fetch`; if it was taken, `dev-charter renumber {new_id}` moves this one on.")


def _guide_for(kind: Kind) -> str:
    return "plan" if kind is CARD else "feature"


@main.group()
def feature() -> None:
    """Features: what a user can do, in their words."""


@feature.command("new")
@click.argument("title")
@click.option("--area", default="", help="The product area it belongs to.")
@click.option("--priority", type=click.Choice(PRIORITIES), default=None, help="Must, Should or Could.")
@click.pass_context
def feature_new(ctx: click.Context, title: str, area: str, priority: str | None) -> None:
    """Create a feature with the next free ID."""
    cfg = _open(ctx)
    new_id, path = store.create(cfg, FEATURE, title, {"area": json.dumps(area), "priority": json.dumps(priority or "")})
    _created(cfg, FEATURE, new_id, path)


@main.group()
def promise() -> None:
    """Promises: rules the whole product keeps, such as 'customers only see their own orders'."""


@promise.command("new")
@click.argument("title")
@click.pass_context
def promise_new(ctx: click.Context, title: str) -> None:
    """Create a promise with the next free ID."""
    cfg = _open(ctx)
    new_id, path = store.create(cfg, PROMISE, title)
    _created(cfg, PROMISE, new_id, path)


@main.group()
def decision() -> None:
    """Decisions: what was decided, instead of what, and why."""


@decision.command("new")
@click.argument("title")
@click.option("--feature", "features", multiple=True, help="A feature or promise it concerns, such as F-014.")
@click.pass_context
def decision_new(ctx: click.Context, title: str, features: tuple[str, ...]) -> None:
    """Record a decision with the next free ID."""
    cfg = _open(ctx)
    _check_refs(features)
    new_id, path = store.create(cfg, DECISION, title, {"features": json.dumps(list(features))})
    _created(cfg, DECISION, new_id, path)


@main.group()
def card() -> None:
    """Task cards: one unit of work, and the checks it serves."""


@card.command("new")
@click.argument("title")
@click.option("--serves", multiple=True, help="A check it serves, such as F-014.a. Repeat for each.")
@click.pass_context
def card_new(ctx: click.Context, title: str, serves: tuple[str, ...]) -> None:
    """Create a task card with the next free ID."""
    cfg = _open(ctx)
    _check_refs(serves)
    new_id, path = store.create(cfg, CARD, title, {"serves": json.dumps(list(serves))})
    _created(cfg, CARD, new_id, path)


@card.command("turn")
@click.argument("card_id")
@click.option("--did", required=True, help="What this turn did, in a few words, such as 'review pass 2'.")
@click.pass_context
def card_turn(ctx: click.Context, card_id: str, did: str) -> None:
    """Record a turn on a card: which agent (or person) did which stage, when, so the card shows who did what when
    agents take turns."""
    cfg = _open(ctx)
    path = store.card_file(cfg, card_id)
    did = " ".join(did.replace("·", "-").split())
    if not did:
        raise CharterError("Say what the turn did, such as --did \"review pass 2\".")
    person = (git.run(cfg.root, "config", "user.name") or "").strip()
    agent = notes.who(cfg.root, ("card", "turn", card_id), person)
    line = f"- {time.strftime('%Y-%m-%d %H:%M')} · {agent} · {did}"
    store.add_turn(path, line)
    click.echo(f"Recorded on {card_id}: {line[2:]}")


def _check_refs(refs: tuple[str, ...]) -> None:
    for ref in refs:
        if not ID_REF_RE.fullmatch(ref):
            raise CharterError(f"'{ref}' is not a feature, promise or check ID, such as F-014 or F-014.a.")


@main.command()
@click.argument("idea")
@click.option("--from", "source", default="", help="Where the idea came from: a card, a feature or a person.")
@click.pass_context
def park(ctx: click.Context, idea: str, source: str) -> None:
    """Write down an idea for later instead of building it now."""
    cfg = _open(ctx)
    path = store.park(cfg, idea, source)
    click.echo(f"Parked in {_shown(cfg, path)}. A person decides whether it becomes work.")


@main.command(name="import")
@click.argument("path", required=False, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--by", "person", default="", help="Who made these decisions. Defaults to your git user name.")
@click.option("--preview", is_flag=True, help="Show what would change, and change nothing.")
@click.pass_context
def import_command(ctx: click.Context, path: Path | None, person: str, preview: bool) -> None:
    """Bring in the decisions and notes made in the My decision and My note columns of LEDGER.xlsx (or a copy)."""
    cfg = _open(ctx)
    ledger = cfg.root / LEDGER_FILE
    path = (path or ledger).resolve()
    if not path.is_file():
        raise CharterError(f"{path} not found. Run `dev-charter report` to build {LEDGER_FILE}, make your decisions "
                           "in its yellow columns, save it, then import it.")
    project = store.load_project(cfg)
    if project.problems:
        lines = "\n".join(f"  {p.where(cfg.root)}: {p.message}" for p in project.problems)
        raise CharterError(f"Nothing was imported, so no decision lands in a file that cannot be read. Fix these "
                           f"first:\n{lines}")
    review = owner_review.plan(project, owner_review.read_sheet(path))
    for item in review.skipped:
        click.echo(f"Skipped {item}: it is no longer in {config.CHARTER_DIR}/.")
    if review.problems:
        lines = "\n".join(f"  {problem}" for problem in review.problems)
        raise CharterError(f"Nothing was imported. Correct these cells in the spreadsheet, save it, and import "
                           f"again:\n{lines}")
    if not review.changes and not review.notes:
        click.echo("Nothing to import: every decision already matches the charter, and there are no notes.")
        return
    for change in review.changes:
        click.echo(f"  {change.entry.id} {change.entry.title}: {change.before} → {change.choice}")
    for entry, note in review.notes:
        click.echo(f"  {entry.id} note: {note}")
    if preview:
        click.echo("Preview only: nothing was changed.")
        return
    person = person or (git.run(cfg.root, "config", "user.name") or "").strip()
    if not person:
        raise CharterError('Say who made these decisions: dev-charter import --by "Your name".')
    for changed in owner_review.apply(cfg, review, person):
        click.echo(f"Changed {_shown(cfg, changed)}.")
    paths, waiting = write_reports(take_snapshot(store.load_project(cfg), trace_module.collect(cfg),
                                                 wip.collect(cfg)), replace_review=path == ledger.resolve())
    if waiting:
        click.echo(kept_message(waiting))
    click.echo("Rebuilt " + " and ".join(_shown(cfg, p) for p in paths) + "; reopen it to see the result.")
    if review.notes:
        click.echo(f"The notes are in {config.CHARTER_DIR}/{owner_review.NOTES_FILE}: your coding agent goes through "
                   "them with you and changes nothing until you agree.")


@main.command(name="renumber")
@click.argument("item_id")
@click.option("--to", "new_id", default=None, help="The new ID. Defaults to the next one never used.")
@click.pass_context
def renumber_command(ctx: click.Context, item_id: str, new_id: str | None) -> None:
    """Move a feature, promise, decision or card to a new ID, with every reference to it."""
    cfg = _open(ctx)
    trace = trace_module.collect(cfg)
    done = renumber.renumber(cfg, store.load_project(cfg), trace, item_id, new_id)
    click.echo(f"Renumbered {done.old} to {done.new}: {_shown(cfg, done.path)}.")
    for path, line, text in done.changed:
        click.echo(f"  changed {_shown(cfg, path)}:{line}  {text}")
    if done.listed:
        click.echo(f"These lines still mention {done.old} and were left alone; check each one:")
        for path, line, text in done.listed:
            click.echo(f"  {_shown(cfg, path)}:{line}  {text}")
    click.echo("Run the tests again so their results use the new ID.")


# --- reading the charter ---------------------------------------------------------------------------------------------


@main.command()
@click.argument("stage", required=False)
def guide(stage: str | None) -> None:
    """Print the guide for a stage of work. Without a stage, list them."""
    if stage is None:
        click.echo("Guides (dev-charter guide <stage>):")
        for name, what in guides.STAGES.items():
            click.echo(f"  {name:<11} {what}")
        return
    if stage not in guides.STAGES:
        raise CharterError(f"There is no guide called '{stage}'. The guides are: {', '.join(guides.STAGES)}.")
    click.echo(guides.read(stage), nl=False)


@main.command()
@click.option("--quiet", is_flag=True, help="Print nothing unless something is wrong.")
@click.pass_context
def report(ctx: click.Context, quiet: bool) -> None:
    """Rebuild LEDGER.xlsx and status.html from the files in charter/."""
    cfg = _open(ctx)
    project = store.load_project(cfg)
    if project.problems:
        lines = "\n".join(f"  {p.where(cfg.root)}: {p.message}" for p in project.problems)
        raise CharterError(f"The report was not rebuilt, so it never leaves out a feature. Fix these first:\n{lines}")
    paths, waiting = write_reports(take_snapshot(project, trace_module.collect(cfg), wip.collect(cfg)))
    if waiting:
        click.echo(kept_message(waiting))
    if not quiet:
        click.echo("Rebuilt " + " and ".join(_shown(cfg, p) for p in paths) + ".")


@main.command()
@click.option("--brief", is_flag=True, help="A few lines, for the start of a working session.")
@click.option("--session-start", is_flag=True, hidden=True, help="Run by the plugin as an agent's session starts.")
@click.pass_context
def status(ctx: click.Context, brief: bool, session_start: bool) -> None:
    """Where the product stands."""
    cfg = _open(ctx)
    project = store.load_project(cfg)
    snap = take_snapshot(project, trace_module.collect(cfg), wip.collect(cfg))
    until = guard_module.strict_until(cfg)
    if cfg.mode == "strict" or not until:
        mode = cfg.mode
    elif until == guard_module.FOREVER:
        mode = f"{cfg.mode}, Strict until a person turns it off"
    else:
        mode = f"{cfg.mode}, Strict until {until:%H:%M}"
    click.echo(f"{cfg.product} · mode {mode} · Dev Charter {__version__}")
    for line in notes.status_lines(cfg.root, session_start):
        click.echo(line)
    for label, entries in (("Features", project.features), ("Promises", project.promises)):
        counts = snap.counts(entries)
        parts = " · ".join(f"{counts[name]} {name}" for name in ORDER if counts[name])
        click.echo(f"{label}: {len(entries)}" + (f" ({parts})" if parts else ""))
    done, active = snap.proven_share()
    if active:
        click.echo(f"Proven or live: {done} of {active} agreed features")
    open_cards = [c for c in project.cards if c.state == "open"]
    for card_ in open_cards:
        click.echo(f"Open card {card_.id} {card_.title} ({', '.join(card_.serves) or 'serves nothing yet'})"
                   + (f": next step: {card_.next_step}" if card_.next_step else ""))
    if not open_cards:
        latest = max(project.cards, key=lambda c: c.path.stat().st_mtime, default=None)
        if latest and latest.next_step:
            click.echo(f"Next step (from {latest.id}): {latest.next_step}")
    shown = snap.wip.branches[: (5 if brief else len(snap.wip.branches))]
    if shown:
        click.echo(f"Work in progress on other branches (not yet merged into {snap.wip.base}):")
        for work in shown:
            cards = "; ".join(f"{c.id} {c.title} ({', '.join(c.serves)})" for c in work.cards)
            click.echo(f"  {work.branch.name} ({work.branch.author}, {work.when:%d %b}"
                       f"{'' if work.branch.pushed else ', not pushed'}): {cards}")
    try:
        waiting = owner_review.unimported(project, cfg.root / LEDGER_FILE)
    except CharterError:
        waiting = None
    if waiting:
        click.echo(f"{LEDGER_FILE} holds a review not imported yet ({waiting.summary()}): import it when the person "
                   "asks (`dev-charter import`).")
    review_notes = owner_review.open_notes(cfg)
    if review_notes:
        click.echo(f"{review_notes} review note{'s' if review_notes != 1 else ''} waiting in {config.CHARTER_DIR}/"
                   f"{owner_review.NOTES_FILE}: go through them with the person who wrote them.")
    if hooks.missing_checks(cfg):
        click.echo("Commits in this clone are not checked yet: run `dev-charter sync`.")
    if project.problems:
        click.echo(f"{len(project.problems)} file(s) have problems; run `dev-charter check`.")
    if brief:
        return
    for name in ORDER:
        members = [e for e in project.entries if snap.of(e).name == name]
        if members:
            click.echo(f"\n{name}:")
            for entry in sorted(members, key=lambda e: e.id):
                click.echo(f"  {entry.id}  {entry.title}  ({snap.of(entry).checks})")


@main.command(name="check")
@click.option("--staged", is_flag=True, help="Check only what is about to be committed in this repository (used by the "
              "commit check).")
@click.pass_context
def check_command(ctx: click.Context, staged: bool) -> None:
    """Check the charter and the code: problems to fix, and warnings worth a look."""
    cfg = _open(ctx)
    repos = cfg.repos
    if staged:
        here = git.toplevel(Path.cwd())
        repos = tuple(r for r in cfg.repos if r.path.resolve() == here)
        if not repos:
            click.echo(f"{Path.cwd()} is not one of the repositories in {config.CONFIG_FILE}; this commit was not "
                       "checked.")
            return
    changes = {repo.path / rel: kind for repo in repos for rel, kind in git.changes(repo.path, staged).items()}
    findings = check.run(store.load_project(cfg), trace_module.collect(cfg), changes, staged=staged)
    problems = [f for f in findings if f.level == check.PROBLEM]
    for finding in findings:
        where = finding.where(cfg.root)
        label = "Problem" if finding.level == check.PROBLEM else "Warning"
        click.echo(f"{label}: {finding.message}" + (f"  ({where})" if where else ""))
    warnings = len(findings) - len(problems)
    if not findings:
        click.echo("All clear.")
    else:
        click.echo(f"\n{len(problems)} problem(s) to fix, {warnings} warning(s).")
    if problems:
        if staged:
            click.echo("The commit was stopped. Fix the problems above, then commit again.")
        ctx.exit(1)


# --- The coding agents' hooks and CI ---------------------------------------------------------------------------------


@main.command(name="strict")
@click.argument("switch", type=click.Choice(["on", "off"]))
@click.option("--hours", default=12.0, show_default=True, help="How long Strict mode stays on.")
@click.pass_context
def strict_command(ctx: click.Context, switch: str, hours: float) -> None:
    """Turn Strict mode on or off in this clone only, for an unattended run: the coding agent may then change only the
    paths an open task card allows."""
    cfg = _open(ctx)
    if switch == "on":
        until = guard_module.turn_on(cfg, hours)
        click.echo(f"Strict mode is on in this clone until {until:%d %b %H:%M}. The coding agent can change only the "
                   "Allowed paths of open task cards, never a sign-off, a state or Dev Charter's settings, and "
                   "cannot turn Strict mode off.")
    else:
        guard_module.turn_off(cfg)
        click.echo(f"Strict mode is off in this clone; the product's mode is {cfg.mode}.")


@main.command(hidden=True)
def guard() -> None:
    """The agents' PreToolUse hook: refuses an edit or a shell command Strict mode does not allow, and notes each shell
    command for `status`. Prints nothing to allow."""
    try:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            reason = guard_module.unreadable(Path.cwd(), "its hook sent something that is not JSON")
        else:
            reason = guard_module.decide(payload, Path.cwd())
    except Exception as exc:  # outside Strict mode, a broken guard must never stop someone's work
        click.echo(f"Dev Charter's guard could not run ({exc}); the edit was allowed.", err=True)
        return
    if reason:
        click.echo(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                      "permissionDecisionReason": reason}}))


@main.command(hidden=True, name="remind")
def remind_command() -> None:
    """The agents' PostToolUse hook: after an edit, say so when a code file does not say which feature it serves."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        message = remind.note(payload, Path.cwd())
    except Exception as exc:  # a broken reminder must never stop someone's work
        click.echo(f"Dev Charter's reminder could not run ({exc}).", err=True)
        return
    if message:
        click.echo(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message}}))


@main.command(name="tags")
@click.option("--refresh", is_flag=True, help="Rewrite the words in each tag to the charter's current wording.")
@click.pass_context
def tags_command(ctx: click.Context, refresh: bool) -> None:
    """List every `serves:` tag in the code; with --refresh, bring their words in line with the charter."""
    cfg = _open(ctx)
    files = trace_module.collect(cfg).files
    if refresh:
        changed = remind.refresh(cfg, store.load_project(cfg), files)
        for path, line, text in changed:
            click.echo(f"  {_shown(cfg, path)}:{line}  {text}")
        click.echo(f"Refreshed {len(changed)} tag(s).")
        return
    count = 0
    for code in sorted(files, key=lambda f: (f.repo.name, f.path)):
        for tag in code.tags:
            count += 1
            what = ", ".join(tag.refs) or "foundation"
            click.echo(f"{code.repo.name}: {code.path}:{tag.line}  {what}" + (f" — {tag.words}" if tag.words else ""))
    untagged = sum(1 for f in files if not f.tags)
    click.echo(f"{count} tag(s); {untagged} code file(s) with none.")


@main.command(name="pr-summary")
@click.option("--base", required=True, help="The branch the pull request merges into, such as origin/main.")
@click.option("--comment", is_flag=True, help="Also post it on the pull request (needs GH_TOKEN and PR_NUMBER).")
@click.pass_context
def pr_summary(ctx: click.Context, base: str, comment: bool) -> None:
    """Summarise, in plain English, what a pull request changes in the product; fail on what must be fixed."""
    cfg = _open(ctx)
    summary = pr.summarise(cfg, store.load_project(cfg), trace_module.collect(cfg), base)
    click.echo(summary.markdown)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(summary.markdown)
    if comment and os.environ.get("PR_NUMBER"):
        _post_comment(cfg.root, os.environ["PR_NUMBER"], summary.markdown)
    if summary.problems:
        ctx.exit(1)


def _post_comment(root: Path, number: str, body: str) -> None:
    import subprocess

    marker = "<!-- dev-charter summary -->"
    for args in (["gh", "pr", "comment", number, "--edit-last", "--body", marker + "\n" + body],
                 ["gh", "pr", "comment", number, "--body", marker + "\n" + body]):
        if subprocess.run(args, cwd=root, capture_output=True).returncode == 0:
            return
    click.echo("The summary could not be posted on the pull request (it is in the job summary instead).", err=True)


@main.command(name="publish")
@click.option("--branch", default=publish.LEDGER_BRANCH, show_default=True, help="The branch the ledger goes on.")
@click.pass_context
def publish_command(ctx: click.Context, branch: str) -> None:
    """Put LEDGER.xlsx and status.html on the team's ledger branch (run by CI after each merge)."""
    cfg = _open(ctx)
    commit = publish.publish(cfg, branch)
    click.echo(f"The team's ledger is on the `{branch}` branch ({commit[:7]}).")
