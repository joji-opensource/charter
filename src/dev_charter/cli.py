# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The `dev-charter` command: a thin layer over the modules, speaking plain English."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import click

from . import __version__, agents, check, config, git, guides, hooks, store
from . import trace as trace_module
from .errors import CharterError
from .model import CARD, DECISION, FEATURE, PRIORITIES, PROMISE, Kind
from .report import GENERATED, take_snapshot, write_reports
from .status import ORDER

ID_REF_RE = re.compile(r"^[FP]-\d{3,}(\.[a-z])?$")


class Command(click.Group):
    """Shows a CharterError as one plain line instead of a traceback."""

    def invoke(self, ctx: click.Context):
        try:
            return super().invoke(ctx)
        except CharterError as exc:
            raise click.ClickException(str(exc)) from exc


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
@click.option("--yes", is_flag=True, help="Use the defaults for anything not given; ask nothing.")
@click.pass_context
def init(ctx: click.Context, name, mode, repos, areas, roles, yes) -> None:
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
            config.render(name or root.name, mode or "standard", repos, list(roles), list(areas)), encoding="utf-8"
        )
        done.append(f"created {config.CONFIG_FILE}")

    charter_dir = root / config.CHARTER_DIR
    for kind in (FEATURE, PROMISE, DECISION, CARD):
        folder = charter_dir / kind.folder
        if not folder.is_dir():
            folder.mkdir(parents=True)
            (folder / ".gitkeep").touch()
            done.append(f"created {config.CHARTER_DIR}/{kind.folder}/")
    for filename in (store.IDEAS_FILE, store.HANDOFF_FILE):
        path = charter_dir / filename
        if not path.exists():
            path.write_text(store.template(filename), encoding="utf-8")
            done.append(f"created {config.CHARTER_DIR}/{filename}")

    outcome = agents.write_block(root)
    if outcome != "unchanged":
        done.append(f"{outcome} the Dev Charter section of {agents.AGENTS_FILE}")
    if _ignore_generated(root):
        done.append("added LEDGER.xlsx and status.html to .gitignore")
    done += hooks.install(config.load(root))

    click.echo(f"Dev Charter is set up in {root}.")
    for line in done:
        click.echo(f"  - {line}")
    click.echo('Next: add your first feature with `dev-charter feature new "<title>"`, or ask your coding agent to.')


def _split(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _ignore_generated(root: Path) -> bool:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    present = {line.strip().lstrip("/") for line in text.splitlines()}
    missing = [name for name in GENERATED if name not in present]
    if not missing:
        return False
    prefix = text if not text or text.endswith("\n") else text + "\n"
    block = ("\n" if prefix else "") + "# Dev Charter: generated views, rebuilt by `dev-charter report`\n"
    path.write_text(prefix + block + "".join(f"/{name}\n" for name in missing), encoding="utf-8")
    return True


@main.command()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Refresh what Dev Charter manages (the AGENTS.md section and the git hooks) after an upgrade or a change of
    mode."""
    cfg = _open(ctx)
    outcome = agents.write_block(cfg.root)
    click.echo(f"{agents.AGENTS_FILE}: {outcome}.")
    for note in hooks.install(cfg):
        click.echo(note)


# --- adding to the charter -------------------------------------------------------------------------------------------


def _created(cfg: config.Config, kind: Kind, new_id: str, path: Path) -> None:
    click.echo(f"Created {new_id} in {_shown(cfg, path)}.")
    click.echo(f"Fill in every line marked <…>, following `dev-charter guide {_guide_for(kind)}`.")


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
    paths = write_reports(take_snapshot(project, trace_module.collect(cfg)))
    if not quiet:
        click.echo("Rebuilt " + " and ".join(_shown(cfg, p) for p in paths) + ".")


@main.command()
@click.option("--brief", is_flag=True, help="A few lines, for the start of a working session.")
@click.pass_context
def status(ctx: click.Context, brief: bool) -> None:
    """Where the product stands."""
    cfg = _open(ctx)
    project = store.load_project(cfg)
    snap = take_snapshot(project, trace_module.collect(cfg))
    click.echo(f"{cfg.product} · mode {cfg.mode} · Dev Charter {__version__}")
    for label, entries in (("Features", project.features), ("Promises", project.promises)):
        counts = snap.counts(entries)
        parts = " · ".join(f"{counts[name]} {name}" for name in ORDER if counts[name])
        click.echo(f"{label}: {len(entries)}" + (f" ({parts})" if parts else ""))
    done, active = snap.proven_share()
    if active:
        click.echo(f"Proven or live: {done} of {active} agreed features")
    open_cards = [c for c in project.cards if c.state == "open"]
    if open_cards:
        click.echo("Open cards: " + "; ".join(f"{c.id} {c.title} ({', '.join(c.serves) or 'serves nothing yet'})"
                                             for c in open_cards))
    next_step = _next_step(cfg)
    if next_step:
        click.echo(f"Next step (handoff): {next_step}")
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


def _next_step(cfg: config.Config) -> str:
    path = cfg.charter_dir / store.HANDOFF_FILE
    if not path.is_file():
        return ""
    in_section = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_section = line[3:].strip().lower() == "exact next step"
            continue
        text = line.strip().lstrip("-").strip()
        if in_section and text and not text.startswith("<!--"):
            return text
    return ""


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
