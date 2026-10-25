# Feature: turn a request into a feature or a promise

A feature says what someone can do, in their words, and what "done" means. A product owner reads it, so it is
written for them, not for engineers.

1. **Look first.** Read `charter/features/` and `charter/promises/`. If an existing one already covers the request,
   propose a change to it instead of a new one.
2. **Create the file.** Run `dev-charter feature new "<short title>"`, adding `--area "<area>"` and
   `--priority Must|Should|Could` when known. It prints the file and its ID. Never write an ID yourself. If a
   teammate's branch already used that ID, `dev-charter renumber F-nnn` moves yours, with every reference to it.
3. **Fill it in.**
   - **As a**: one role from `charter.toml` (`[words] roles`).
   - **I want to**: what they want to do, in their words.
   - **With**: the details that matter to them.
   - **Must also**: speed, privacy, devices or limits, in plain words. Delete the line if there are none.
   - **So that**: the outcome for them, not for the system.
   - **Done means**: one line per thing a person or a test can check (`a.`, `b.`, `c.` …). Specific and observable
     ("a text message is sent when the order goes out for delivery"), never vague ("works well", "is fast").
4. **Keep it short.** Under 250 words. Longer usually means two features.
5. **Leave `state: idea`.** The person moves it to `agreed`. Never write a sign-off.
6. **Reply with the feature and your additions.** Show what you wrote, and list every Done-means line the person did
   not ask for, so they keep or remove it. Ask about anything you guessed.

## Promises

A promise is a rule the whole product keeps, such as "customers only ever see their own orders". Create it with
`dev-charter promise new "<title>"`, write **We promise** in a customer's words, **Applies to** where it holds, and
**Done means** the same way as for a feature.

## Decisions

When the person decides something non-obvious, record it with `dev-charter decision new "<title>" --feature F-nnn`:
**Decision**, **Instead of** (what was not chosen) and **Because**. Add its ID to the feature's `decisions` list.
