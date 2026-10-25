---
name: strict
description: Turn Strict mode on or off in this clone, for an unattended run: Claude Code may then change only what an open task card allows.
argument-hint: on or off
allowed-tools: Bash(dev-charter strict:*), Bash(dev-charter status:*)
---

Run `dev-charter strict $ARGUMENTS`. If it is now on, check that the open task card lists the files the
work needs under '## Allowed paths' (`dev-charter status --brief` shows the open cards), and say which ones.
