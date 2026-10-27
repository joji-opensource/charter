# Commands: everything `dev-charter` does, and when to use it

Run any command with `--help` for its options. Commands that change files print every file they changed.

## Every working session

| Command | Use it to |
|---|---|
| `dev-charter status --brief` | See where the product stands, your open cards and their next steps, and the open cards on teammates' branches. First thing in every session. |
| `dev-charter guide <stage>` | Load the guide for a stage: `principles`, `feature`, `plan`, `review`, `probe`, `build`, `verify`, `ship`, `commands`. |
| `dev-charter check` | Find problems in the charter and the trace (malformed files, unknown IDs, untagged new code). Run it before saying work is done. |
| `dev-charter report` | Rebuild `LEDGER.xlsx` and `status.html`. Also runs after every commit. |

## Adding to the charter

| Command | Use it to |
|---|---|
| `dev-charter feature new "<title>"` | Create a feature with the next free ID (`--area`, `--priority Must/Should/Could`). Then fill in the file it prints. |
| `dev-charter promise new "<title>"` | Create a promise: a rule the whole product keeps. |
| `dev-charter decision new "<title>"` | Record a decision (`--feature F-014` for each feature it concerns). |
| `dev-charter card new "<title>"` | Create a task card (`--serves F-014.a` for each check it serves). |
| `dev-charter card turn CARD-nnn --did "<what you did>"` | Record a turn on a card when you hand it on or stop: the date, who (the agent, from its hook; or you) and what the turn did. |
| `dev-charter park "<idea>"` | Write down an idea that is not the task (`--from` where it came from), instead of building it. |

Never write an ID yourself; these commands hand them out so they stay unique across branches.

## The product owner's review

| Command | Use it to |
|---|---|
| `dev-charter import` | Bring in the decisions and notes a person made in the My decision and My note columns of `LEDGER.xlsx`, only when they ask. It names every change; `--preview` shows them and changes nothing, `--by "<name>"` says who decided (default: the git user name), and a file path imports a copy, such as one downloaded from Google Sheets. |

Notes arrive in `charter/review-notes.md`: go through each with its author, and delete it once it is dealt with.

## Tags in the code

| Command | Use it to |
|---|---|
| `dev-charter tags` | List every `serves:` tag in the code, and how many code files have none. |
| `dev-charter tags --refresh` | Rewrite the words in tags to the charter's current wording, when a person asks for it. |
| `dev-charter renumber F-017` | Move an item to the next free ID when a teammate's branch already used it, with every reference: files, tags, test names (`--to` to choose the ID). |

## Setting up and keeping up

| Command | Use it to |
|---|---|
| `dev-charter init` | Set up Dev Charter in a product (a person usually asks for the plugin's `init` skill). Safe to run again. |
| `dev-charter sync` | Refresh the `AGENTS.md` section, the pointers to it in child repositories, and the git hooks after an upgrade, a change of mode, or a fresh clone. An agent's sandbox may not let it write git hooks; then the person runs it. |
| `dev-charter strict on` / `off` | Turn Strict mode on in this clone for an unattended run (`--hours`). Only a person turns it off, from their own terminal: the guard refuses `strict off` from an agent. |
| `dev-charter ci` | Write the GitHub workflow that checks each pull request and keeps the team's ledger on the `ledger` branch. |

## Run by hooks and CI, not by hand

`dev-charter guard` (before each edit and shell command: Strict mode, and a note that lets `status` tell whether the
guardrails are running), `dev-charter remind` (after each edit, when a code file has no tag), `dev-charter pr-summary
--base <branch>` and `dev-charter publish` (in CI).

## In Claude Code and Codex, with the plugin

The plugin's skills are `init`, `feature`, `plan`, `review`, `probe`, `build`, `verify`, `ship`, `status`, `park`,
`import` and `strict`. In Claude Code, call one as `/dev-charter:plan`; in Codex, as `$dev-charter:plan`, or choose it
from `/skills`. Codex runs the plugin's hooks only once the person trusts them in `/hooks`, and again after each update
that changes them; until then `dev-charter status --brief` says the guardrails are not running.
