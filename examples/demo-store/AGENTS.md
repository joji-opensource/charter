<!-- dev-charter:start v0.1 -->
## Dev Charter: how work is done in this repository

This product's features, promises and decisions live in `charter/`, written in plain English for the people who own
the product. `LEDGER.xlsx` and `status.html` are generated from them; never edit those two files.

- Every change serves a feature (`F-nnn`) or a promise (`P-nnn`) in `charter/`. If none fits, ask; never invent one.
- At the start of work, run `dev-charter status --brief`. It lists the work in progress on other people's branches:
  do not start work one of them is already doing; say so and ask.
- Before each stage, run `dev-charter guide <stage>` and follow it. The stages are feature, plan, review, probe,
  build, verify and ship; `dev-charter guide principles` applies to all of them.
- Create features, promises, decisions and task cards with `dev-charter feature new "<title>"` (or `promise`,
  `decision`, `card`), then fill in the file it prints. Never write an ID yourself.
- Put `serves: F-nnn` in a comment near the top of each new code file, and the check's ID in each test's name
  (`test_F014_b_text_sent`).
- An idea that is not the task goes to `dev-charter park "<idea>"`, never into code.
- Before saying work is done, run `dev-charter check` and fix what it reports.
- Never write a sign-off, never change the `state` of a feature or promise, and never commit with `--no-verify`:
  people do those.
<!-- dev-charter:end -->
