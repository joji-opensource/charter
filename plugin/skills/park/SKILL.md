---
name: park
description: Write an idea down for later instead of building it now.
argument-hint: the idea
allowed-tools: Bash(dev-charter park:*)
---

Take the idea from what the person asked (in Claude Code it is here: $ARGUMENTS) and run `dev-charter park "<the
idea>"`, adding `--from "<card, feature or person>"` when you know where it came from. Confirm in one line that it is parked and that a person decides whether it becomes work.
