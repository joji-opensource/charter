---
name: import
description: Bring in the product owner's decisions and notes from the My decision and My note columns of LEDGER.xlsx.
argument-hint: a copy of LEDGER.xlsx to import, if not the one in the project folder
allowed-tools: Bash(dev-charter import:*)
---

Run `dev-charter import $ARGUMENTS`. Tell the person, in their words, what changed: each item and its new decision,
and how many notes arrived. If it imported nothing because some cells cannot be applied, list those cells and what to
choose instead. If notes arrived, offer to go through them one at a time from `charter/review-notes.md`; change nothing
a note asks for until the person agrees, and delete each note once it is dealt with.
