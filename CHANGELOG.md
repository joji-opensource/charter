# Changelog

## 0.2.0 — 2026-10-27

- **Codex, as well as Claude Code.** One plugin serves both agents: Codex installs it with `codex plugin marketplace
  add joji-opensource/charter` and `codex plugin add dev-charter@dev-charter`, and calls its skills as
  `$dev-charter:plan`. Codex runs the plugin's hooks once you trust them in `/hooks`, and again after each update that
  changes them.
- **The guardrails read both agents' edits.** Strict mode and the reminder to tag code understand Codex's patches,
  file by file: a patch with one file outside the task card is refused whole. States and sign-offs are read as Dev
  Charter reads them everywhere else, so a duplicated `state:` or an indented sign-off no longer slips past, and a
  feature file with a detail written twice is reported by `check`.
- **Strict mode keeps its own settings.** The agent cannot turn it off, nor change `charter.toml` or `.dev-charter/`;
  when the guard cannot tell whether a change is allowed, it refuses.
- **Guardrails that say when they are off.** The guard now also sees each shell command, and `status --brief` says when
  it did not run for the agent's own command: the plugin is missing or older, or Codex has not been told to trust its
  hooks. Two agents working in one folder never answer for each other. At session start, the plugin says when the
  `dev-charter` command is missing or older than it.
- **Products of several repositories.** Each child repository's `AGENTS.md` gets a short pointer to the root's rules,
  because Codex started inside one would not find them otherwise. `check` reports a missing pointer, an
  `AGENTS.override.md` (which Codex reads instead), and a section past the first 32 KiB Codex reads.
- **Plain words when a write is refused.** A coding agent's sandbox lets it write only inside the folder it was started
  in, and never in `.git`; Dev Charter now says so and what to do, never a traceback. `init` and `sync` carry on past git
  hooks they cannot write, and say to run `dev-charter sync` from a terminal.
- **Taking turns.** `dev-charter card turn CARD-005 --did "review pass 2"` adds a line to the card's new Turns section
  (date · agent · what the turn did), naming the agent from its hook. The rules ask for it whenever an agent hands a
  card on or stops, and the review guide describes a second review by another agent that does not start from the
  first one's conclusions.
- **Upgrading in one command.** `dev-charter sync --upgrade` moves a project set up for an older Dev Charter to this
  one: the pin in `charter.toml` (changed last, so running it again finishes the job), the install line of the workflow
  `dev-charter ci` wrote, the `AGENTS.md` section and the git hooks. A project that needs a newer Dev Charter is never
  moved back. After upgrading Dev Charter, run it in each project, then update the plugin in each agent.

## 0.1.3 — 2026-10-25

- **Decide in the spreadsheet.** The Features and Promises tabs of `LEDGER.xlsx` have two yellow columns for the
  product owner: **My decision**, a dropdown (Not reviewed, Agree, Agree (Must), Agree (Should), Agree (Could), Defer,
  Cut; promises have no priority), opening on each item's current decision, and **My note**.
- **`dev-charter import`** brings them in: it changes only the `state:` and `priority:` lines of the items you changed
  (Agree → agreed, keeping a live item live; Defer → parked; Cut → retired), logs each decision with who and when in
  `charter/review-log.md`, collects notes in `charter/review-notes.md`, and rebuilds the spreadsheet. It applies all
  or nothing, finds columns by name and rows by ID (so sorting or moving columns is fine), and imports any copy, such
  as one from Google Sheets: `dev-charter import ~/Downloads/LEDGER.xlsx`. `--preview` changes nothing.
- **Your review is never overwritten.** While `LEDGER.xlsx` holds a decision or a note not yet imported, the rebuild
  after each commit (and `dev-charter report`) leaves it alone and says so. `status --brief` says when a review is
  waiting and how many review notes are open.
- **The rule for agents changes:** Claude Code changes a state or a priority, or writes a sign-off, only when a person
  explicitly asks and names the items, and says what it changed (before: never). `/dev-charter:import` added. Run
  `dev-charter sync` to update `AGENTS.md`; it also adds the new lines to `.gitignore` (Excel's `~$LEDGER.xlsx`) and
  `.gitattributes` (the two review files merge line by line).

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
