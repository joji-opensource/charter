# Ship: hand off, and prepare the commit

1. **Update `charter/handoff.md`** with only the current state: what was done (with the evidence: the test, the
   output, the screen), what is in progress and exactly where it stopped, what was parked, and the exact next step.
   The next session, or the next person, starts from it.
2. **Close the card** by setting its `state: done`, if its Done when passed.
3. **Run `dev-charter check`** and fix every problem it reports.
4. **Commit only when the person asks.** Otherwise stage the files the card touched, and nothing that wandered in,
   and show the commit message you propose.
5. **The commit message**: one logical change per commit; a prefix (`feat:`, `fix:`, `docs:`, `refactor:`,
   `test:`, `chore:`); a subject under 72 characters in the imperative ("add delivery date to the order page"); and
   a line naming what it serves:

   ```
   feat: show the expected delivery date on the order page

   Serves: F-014.a
   ```

6. **Never** commit with `--no-verify`, force-push, or rewrite history that others already have.
7. **A pull request** says: the card, the checks it serves, what changed (three lines), how it was verified and the
   result, and anything parked or any blocker noted on the card.
