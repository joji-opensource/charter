# Changelog

## 0.1.2 — 2026-10-25

- **`check` notices when the rules in `AGENTS.md` are out of date**, even within a minor release: it compares the
  Dev Charter section's text with what the installed version would write, not just its version. It tells apart a
  section from an earlier release (run `dev-charter sync`), one edited by hand inside the section (`sync` restores
  it; put your own rules outside it), and one written by a newer Dev Charter (upgrade yours instead).
- **`sync` never downgrades the section.** A teammate on an older release leaves a newer section alone, so teammates
  on different releases never rewrite it back and forth. The section's marker now records the full version.

## 0.1.1 — 2026-10-25

- **Code that explains itself.** Tags can carry words (`serves: F-014 — Track my order`) and can name a single check
  (`serves: F-014.c — …`) above the function that delivers it. Every tag in a file now counts (0.1.0 read only the
  first). The spreadsheet shows which file and line delivers each check, and the Code map lists every tag.
- **Told while building.** With the plugin, Claude Code is reminded right after it edits a code file with no tag,
  with the exact tag for the task card it is working on.
- **`dev-charter tags`** lists every tag; **`tags --refresh`** rewrites their words to the charter's wording.
- **`dev-charter guide commands`**: every command and when to use it, pointed to from `AGENTS.md`, so Claude Code
  knows them all.
- `check` refuses a tag naming a check that does not exist (`F-014.z`).

## 0.1.0 — 2026-10-25

The first working release, built and tested with Claude Code.

- **Your product's charter in plain English.** Features ("As a … I want to … with … so that …", and what "done"
  means), promises, decisions, task cards and parked ideas, one small file each, with IDs handed out by
  `dev-charter feature new` and friends.
- **The trace.** `serves:` tags link code to features; test names carry the check they prove; test results are read
  from JUnit XML. Status is worked out from tests and people's sign-offs, never typed in: Agreed, Being built, Built,
  Proven, Live, At risk.
- **LEDGER.xlsx and status.html**, rebuilt after every commit: Summary, Features (with Built in and Proven by),
  Promises, Code map (linked to GitHub at the exact commit), Work in progress, Decisions, Ideas.
- **Checks.** `dev-charter check`, and a git hook that stops a commit adding code that serves no feature.
- **Instructions for Claude Code** in `AGENTS.md`, and eight stage guides (`dev-charter guide`).
- **Team work.** IDs that never collide once fetched and are never reused; `dev-charter renumber`; a handoff per card;
  ideas that merge line by line; work in progress on every branch; product-owner approval through CODEOWNERS.
- **Claude Code plugin.** `/dev-charter:init`, `:feature`, `:plan`, `:review`, `:probe`, `:build`, `:verify`,
  `:ship`, `:status`, `:park`, `:strict`; status at the start of each session; Strict mode's edit guard.
- **CI.** `dev-charter ci` writes a GitHub workflow: a plain-English summary and checks on each pull request, and the
  team's ledger on a `ledger` branch after each merge.

## 0.0.1 — 2026-10-25

Held the name on PyPI.
