# Build: only what the task card serves, reversibly

## Stay on the card

Build what the open card's checks need, nothing more. Anything else goes to `dev-charter park "<idea>"`. Recognise
these, because each one looks reasonable and together they build a different product:

- "While I'm here…" and "I also noticed…"
- the refactor next door;
- "for robustness I added…" and error handling beyond what the checks need;
- "generalised for future use", or a setting "for flexibility";
- a fix that turns into a redesign.

**The blocker test** is the only exception. A change outside the card is allowed only when all three hold: a check
on the card cannot pass without it; there is no way round it inside the card; and the change is the smallest that
unblocks. Note it under **Blockers** on the card (date · file · why), add the file to **Allowed paths** in Strict
mode, and make it. If it is large, or touches code other work depends on, stop and ask instead.

## Build so it can be undone

- Put a new path behind the existing interface and keep the old one until the new one passes the old one's tests.
- Ship risky paths switched off, so turning them off is a setting, not a revert.
- Where output must not change, keep a copy of the expected output and compare exactly.

## Leave a trail

- Tag what you write. At the top of every new code file: `serves: F-014 — Track my order` (several features:
  `serves: F-014, P-001`). Above each function or block that delivers one check: `serves: F-014.c — <the check, in a
  few words>`, so a reader sees why the code exists and the spreadsheet shows which code delivers each check. Code
  that every feature relies on says `serves: foundation`.
- When you change an existing file that has no tag, add one for the feature your card serves. Old code gets explained
  one change at a time. (With the plugin, Claude Code is reminded right after the edit.)
- Name every test after the check it proves: `test_F014_b_text_sent_when_out_for_delivery`.
- Write code that reads like the code around it: its naming, its comments, its habits. Comments say what and why,
  never "changed on" or "was X, now Y".
- Remove dead code and stale comments in the files you are already changing, and not one file further.

## Stop when it cannot be built properly

A missing credential, an unavailable service, an open decision: say so, name what is needed, and stop. Never a stub,
a sample or a hardcoded value to keep moving.

After each step, say what the person can now see or run, and exactly how.
