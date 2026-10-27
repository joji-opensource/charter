---
name: init
description: Set up Dev Charter in this product: ask the product owner six questions, then write the settings, the rules for coding agents and the commit checks.
allowed-tools: Bash(dev-charter init:*), Bash(dev-charter status:*), Bash(dev-charter guide:*), Bash(git branch:*), Bash(git remote:*)
---

Set up Dev Charter in this product folder. If `charter.toml` is already here, say so, run
`dev-charter status --brief`, and stop.

Ask the person these six questions together, in one short message, in plain words:

1. The product's name.
2. Its main areas, such as "Checkout, Accounts, Orders and delivery".
3. The kinds of people who use it, such as "customer, store admin".
4. How strict to be: **light** (checks only in CI), **standard** (every commit is checked; recommended) or
   **strict** (the coding agent may change only what a task card allows).
5. The branch work is merged into. Suggest one from `git branch -r` (the remote's main branch, or `dev` if work
   lands there first).
6. Optional: the product owner's GitHub name, whose approval any change to features, promises or decisions needs.

Then run `dev-charter init --yes` with every answer as a flag: `--name "…"`, one `--area "…"` per area, one
`--role "…"` per role, `--mode …`, `--integration-branch …`, and `--owner @…` if given. If the product spans several
repositories, add one `--repo "<folder>"` for each.

Tell the person, in plain words, what was set up. The next step is to describe a first feature with the
`feature` skill (`/dev-charter:feature` in Claude Code, `$dev-charter:feature` in Codex).
