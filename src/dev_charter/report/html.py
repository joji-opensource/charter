# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""status.html: one self-contained page with where the product stands."""

from __future__ import annotations

from html import escape
from pathlib import Path

from ..model import Entry
from ..status import ORDER
from . import Snapshot

STYLE = """
:root { --bg:#ffffff; --fg:#1f2328; --muted:#59636e; --line:#d1d9e0; --head:#1f3864; --head-fg:#ffffff;
  --at-risk:#f8cbad; --live:#548235; --live-fg:#ffffff; --proven:#a9d08e; --built:#bdd7ee; --being-built:#ffe699;
  --agreed:#e7e6e6; --idea:#ffffff; --parked:#f2f2f2; --retired:#f2f2f2; --chip-fg:#1f2328; }
@media (prefers-color-scheme: dark) { :root { --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1; --line:#3d444d;
  --head:#1f3864; --at-risk:#7a3b1d; --live:#2f5d1f; --proven:#3b5d2a; --built:#24476b; --being-built:#6b5a14;
  --agreed:#3d444d; --idea:#161b22; --parked:#21262d; --retired:#21262d; --chip-fg:#e6edf3; } }
* { box-sizing: border-box; }
body { margin:0; padding:24px 16px; background:var(--bg); color:var(--fg);
  font:15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
main { max-width:1100px; margin:0 auto; }
h1 { margin:0 0 4px; font-size:26px; } h2 { margin:32px 0 8px; font-size:18px; }
.note { color:var(--muted); font-size:13px; margin:0 0 20px; }
.share { font-size:17px; margin:0 0 8px; }
.chips { display:flex; flex-wrap:wrap; gap:8px; margin:0; padding:0; list-style:none; }
.status { display:inline-block; padding:2px 8px; border-radius:10px; font-weight:600; font-size:13px;
  white-space:nowrap; color:var(--chip-fg); border:1px solid var(--line); }
.s-at-risk { background:var(--at-risk); } .s-live { background:var(--live); color:var(--live-fg); }
.s-proven { background:var(--proven); } .s-built { background:var(--built); }
.s-being-built { background:var(--being-built); } .s-agreed { background:var(--agreed); }
.s-idea { background:var(--idea); } .s-parked, .s-retired { background:var(--parked); color:var(--muted); }
.wrap { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th { background:var(--head); color:var(--head-fg); text-align:left; padding:6px 8px; font-weight:600; }
td { border-bottom:1px solid var(--line); padding:8px; vertical-align:top; }
td.id { white-space:nowrap; font-weight:600; }
.story { color:var(--muted); font-size:13px; margin-top:2px; }
ul.plain { margin:0; padding-left:18px; }
.empty { color:var(--muted); }
"""


def _chip(name: str) -> str:
    return f'<span class="status s-{name.lower().replace(" ", "-")}">{escape(name)}</span>'


def _story(entry: Entry) -> str:
    who, want = entry.story.get("As a", ""), entry.story.get("I want to", "")
    if who and want:
        return f"As a {who}, I want to {want}"
    promise = entry.story.get("We promise", "")
    return f"We promise {promise}" if promise else ""


def _entries_table(snap: Snapshot, entries: list[Entry], with_area: bool) -> str:
    if not entries:
        return '<p class="empty">None yet.</p>'
    head = "<tr><th>ID</th><th>What</th>" + ("<th>Area</th>" if with_area else "") + "<th>Status</th></tr>"
    rows = []
    for entry in sorted(entries, key=lambda e: (ORDER.index(snap.of(e).name), e.id)):
        state = snap.of(entry)
        area = f"<td>{escape(entry.area)}</td>" if with_area else ""
        rows.append(
            f'<tr><td class="id">{escape(entry.id)}</td><td>{escape(entry.title)}'
            f'<div class="story">{escape(_story(entry))}</div></td>{area}'
            f'<td>{_chip(state.name)}<div class="story">{escape(state.checks)}</div></td></tr>'
        )
    return f'<div class="wrap"><table>{head}{"".join(rows)}</table></div>'


def render(snap: Snapshot) -> str:
    project = snap.project
    counts = snap.counts(project.features)
    chips = "".join(f"<li>{_chip(name)} {counts[name]}</li>" for name in ORDER if counts[name])
    done, active = snap.proven_share()
    share = f"{done} of {active} agreed features are proven or live." if active else "No features agreed yet."
    decisions = "".join(
        f"<li><strong>{escape(d.id)}</strong> {escape(d.title)}: {escape(d.decision)}</li>"
        for d in sorted(project.decisions, key=lambda d: d.id)
    ) or '<li class="empty">None yet.</li>'
    ideas = "".join(f"<li>{escape(i.text)}</li>" for i in project.ideas) or '<li class="empty">None yet.</li>'
    work = "".join(
        f"<li><strong>{escape(w.branch.name)}</strong> ({escape(w.branch.author)}, {w.when:%d %b}): "
        + "; ".join(f"{escape(c.id)} {escape(c.title)}" + (f" (next: {escape(c.next_step)})" if c.next_step else "")
                    for c in w.cards) + "</li>"
        for w in snap.wip.branches
    ) or '<li class="empty">None found.</li>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(project.config.product)} status</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>{escape(project.config.product)}</h1>
<p class="note">{escape(snap.provenance)} Generated by Dev Charter from the files in charter/; do not edit.</p>
<p class="share">{escape(share)}</p>
<ul class="chips">{chips}</ul>
<h2>Features</h2>
{_entries_table(snap, project.features, with_area=True)}
<h2>Promises</h2>
{_entries_table(snap, project.promises, with_area=False)}
<h2>Work in progress on other branches</h2>
<ul class="plain">{work}</ul>
<h2>Decisions</h2>
<ul class="plain">{decisions}</ul>
<h2>Ideas for later</h2>
<ul class="plain">{ideas}</ul>
</main>
</body>
</html>
"""


def write_html(snap: Snapshot, path: Path) -> None:
    path.write_text(render(snap), encoding="utf-8")
