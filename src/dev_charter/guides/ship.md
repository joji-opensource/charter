# Ship: hand off, and prepare the commit

1. **Update the card's Handoff section** with only the current state: what was done (with the evidence: the test,
   the output, the screen), what is in progress and exactly where it stopped, what was parked, and the next step.
   The next session, or the next person, starts from it. Each card keeps its own handoff, so people working on other
   branches never overwrite each other's.
2. **Record your turn**: `dev-charter card turn CARD-nnn --did "<what this turn did>"`, such as "planned" or "built
   checks a and b". Do it whenever you hand the card on or stop, so the card shows which agent, or person, did which
   stage: git cannot, when a person makes every commit.
3. **Close the card** by setting its `state: done`, if its Done when passed.
4. **Run `dev-charter check`** and fix every problem it reports.
5. **Commit only when the person asks.** Otherwise stage the files the card touched, and nothing that wandered in,
   and show the commit message you propose.
6. **The commit message**: one logical change per commit; a prefix (`feat:`, `fix:`, `docs:`, `refactor:`,
   `test:`, `chore:`); a subject under 72 characters in the imperative ("add delivery date to the order page"); and
   a line naming what it serves:

   ```
   feat: show the expected delivery date on the order page

   Serves: F-014.a
   ```

7. **Never** commit with `--no-verify`, force-push, or rewrite history that others already have.
8. **A pull request** says: the card, the checks it serves, what changed (three lines), how it was verified and the
   result, and anything parked or any blocker noted on the card.
