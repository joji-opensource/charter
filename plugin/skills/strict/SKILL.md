---
name: strict
description: Turn Strict mode on or off in this clone, for an unattended run: the coding agent may then change only what an open task card allows.
argument-hint: on or off
allowed-tools: Bash(dev-charter strict:*), Bash(dev-charter status:*)
---

Take on or off from what the person asked (in Claude Code it is here: $ARGUMENTS). For on, run `dev-charter strict
on`. Only a person turns it off: for off, give them `dev-charter strict off` to run in their own terminal. If it is
now on, check that the open task card lists the files the
work needs under '## Allowed paths' (`dev-charter status --brief` shows the open cards), and say which ones.
