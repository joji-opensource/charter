# Dev Charter

**Know what your product does, which code delivers it, and what is proven — in one spreadsheet.**

Dev Charter keeps a plain-English record of every feature your product promises, links each one to the code that
builds it and the tests that prove it, and turns that into a spreadsheet a founder, product manager or executive
can read in five minutes. It is built for teams who write software with Claude Code, where code now arrives faster
than anyone can read it.

> **Status: early development.** The first working release is being built. Version 0.0.1 on PyPI only holds the
> name and does nothing yet; the commands below describe the first working release. Follow the repository to hear
> when it ships.

---

## The problem

AI coding agents let a small team build a large product quickly. The cost shows up later:

- **Nobody can say what the product actually does today.** The code is there, but the answer to "can a customer
  do X yet, and how do we know?" takes a day of reading or an engineer's opinion.
- **Code grows that no one can explain.** Tens of thousands of lines appear, and no one can point to which
  customer need each part serves, or whether any of it is still needed.
- **Plans pile up as documents.** Designs, reviews and decision notes multiply until they are longer than the code
  and too long to read.
- **"Done" means "the agent said so."** Status is claimed, not proven, and it goes stale the moment the next
  change lands.
- **Scope drifts quietly.** Each "while I'm here" improvement looks reasonable on its own; together they build a
  different product than the one you planned.

## What you get

### For founders and product owners

- **One page that answers "where are we?"** Every feature, in plain English, with its status, in a spreadsheet at
  the root of your project. No technical knowledge needed to read it.
- **Features written the way customers think.** Each one reads *"As a customer, I want to … with … so that …"*,
  followed by what "done" means in plain words. You review the product, not the code.
- **Status you can trust.** A feature only moves to *Built* when its checks pass, and only to *Proven* when a named
  person has seen it work on real data and signed it off. Status is never typed in: it is worked out from the
  checks and the sign-offs, and every sign-off records who and when.
- **Early warning.** A feature that used to work and now fails is flagged *At risk* the next time the
  spreadsheet is generated, before a customer finds it.
- **Control over what gets built.** Every piece of work names the feature it serves. Ideas that don't serve an
  agreed feature are captured in one list for you to decide on later, instead of quietly becoming code.

### For executives, investors and customers

- **A summary you can share.** Features by area and status, the share that is proven, and what changed this week.
- **Claims backed by evidence.** Every "this works" points to the checks behind it and the date it was last
  proven.
- **Release readiness at a glance.** See which features in a release are proven, which are built but unproven, and
  which haven't started.

### For engineers and AI coding agents

- **Every task is tied to a customer need.** The agent knows which feature and which checks its work serves, and
  what is out of bounds.
- **Code that explains itself.** Each module carries a short tag naming the feature it serves. The *Code map* shows
  every module, the features behind it, and the code that serves nothing: candidates to justify or remove.
- **Decisions made once.** One decisions log, plain-English summary first, so settled questions are not reopened
  in every session.
- **Clean handoffs.** Each session ends with where it stopped and the exact next step, so the next session, or the
  next person, starts without guessing.

### Before and after

| Question | Without Dev Charter | With Dev Charter |
|---|---|---|
| Is this feature done? | Ask someone, get an opinion | Open the spreadsheet: calculated status and last proven date |
| Why does this code exist? | Read it, or guess | The *Code map* names the feature it serves |
| What code serves nothing? | Nobody knows | Listed as *Unexplained code* |
| What did we decide, and why? | Spread across chats and documents | One decisions log |
| What changed this week? | A status report someone writes by hand | Generated after every commit |
| Did the agent stay on task? | Find out in code review | Work that serves no feature is flagged before you commit |

## What a feature looks like

```
F-014  ·  Area: Orders and delivery  ·  Priority: Must  ·  Release: Spring launch

As a        customer of an online store
I want to   see where my order is and when it will arrive
With        the current step (packed, shipped, out for delivery), the expected delivery date,
            and a text message when it is out for delivery
Must also   load in under 2 seconds on a phone · show me only my own orders
So that     I don't have to contact support to ask where my package is

Done means
  a. Every order shows its current step and expected delivery date
  b. A text message is sent when the order goes out for delivery
  c. Opening someone else's order shows a sign-in page, never their order

Status      Built: 3 of 3 checks passing                          (calculated)
Built in    shop-api: orders/status.py · notifications/sms.py     (found in the code)
Proven by   7 automated checks (7 passed) · results of 24 Oct 10:42
            1 sign-off by Joji John
Decisions   DEC-001 (delivery dates come from the carrier, never guessed)
```

You write the top half, or ask your agent to. Dev Charter fills in the bottom half from the code and the test results.

**Statuses:** Idea → Agreed → Being built → Built → Proven → Live, plus *At risk*, *Parked* and *Retired*.

**Promises** are product-wide rules that apply to many features, such as *"customers only ever see their own
orders and details"* or *"the price shown is always the price charged"*. They get their own rows and their own
checks.

## How it works

Dev Charter has three layers. You can use the first two on their own.

1. **The Ledger: what and why.** One short text file per feature, promise and decision, kept in your repository.
   People and agents write these.
2. **The Trace: where and how do we know.** A one-line tag in each module (`serves: F-014`) and the feature's ID in
   each test's name (`test_F014_b_text_sent`) link code and tests back to features. Dev Charter scans your
   repositories, in any language, and reads test results in JUnit XML, which pytest and most test runners write
   (Jest and Go through a small add-on).
3. **The Workflow: how the agent works.** Task cards that name the feature they serve, a plan → review → prove →
   build → ship loop, one list for parked ideas, and a handoff at the end of each session.

`dev-charter report` combines all three into `LEDGER.xlsx` and a one-page `status.html`. They are rebuilt after every
commit, on demand, and in CI, and never edited by hand, so they cannot drift from the truth.

### Built for Claude Code

Dev Charter's rules live in your repository, in `AGENTS.md`, which Claude Code reads every time it opens the project,
so every teammate's sessions follow them. The full guide for each stage comes from the installed Dev Charter
(`dev-charter guide plan`), so every project gets the same guides and upgrading Dev Charter upgrades them everywhere. The
Dev Charter plugin adds commands such as `/dev-charter:feature` and `/dev-charter:plan`, and Strict mode.

Other AI coding tools that read `AGENTS.md` are planned for a later release; this release is tested with Claude
Code only.

### The spreadsheet

| Tab | What it shows |
|---|---|
| Summary | Features by area and status, share proven, what changed this week |
| Features | One row per feature, the main view |
| Promises | Product-wide rules and their status |
| Code map | Each module and the features it serves; unexplained code flagged |
| Decisions | Every decision, plain English first |
| Ideas | Everything parked for later |

## Choose how strict to be

| Mode | When Dev Charter checks | Best for |
|---|---|---|
| **Light** | In CI, after work is merged | Prototypes, adding Dev Charter to an existing project gradually, teams without AI agents |
| **Standard** | Before each commit | Everyday work where a person reviews and commits |
| **Strict** | At every file change: Claude Code is blocked from writing outside its task | Long unattended agent runs, several agents at once, shared core code |

Switch modes with one line in `charter.toml`, or turn on Strict for a single session.

## Getting started

**1. Install Dev Charter** (once per machine, in a terminal):

```bash
uv tool install dev-charter
```

**2. Add the Dev Charter plugin** (once per machine, inside Claude Code):

```
/plugin marketplace add joji-opensource/charter
/plugin install dev-charter@dev-charter
```

**3. Set up your project** (open Claude Code in your project folder):

```
/dev-charter:init
```

Claude asks five questions (product name, repositories, product areas, user roles, how strict to be) and sets
everything up. Prefer the terminal? `dev-charter init` asks the same questions.

**4. Work**

```
/dev-charter:feature  As a customer I want to save products for later …
/dev-charter:status   where are we?
```

`LEDGER.xlsx` and `status.html` are rebuilt after every commit; `dev-charter report` rebuilds them any time.

So that statuses include your tests, have your test runner write JUnit XML (with pytest:
`pytest --junitxml=reports/junit.xml`) and tell Dev Charter where, with `results = ["reports/*.xml"]` in
`charter.toml`. Name each test after the check it proves: `test_F014_b_text_sent`.

`/dev-charter:init` adds only your product's own content to your project: a `charter.toml` settings file, a `charter/`
folder with your features, promises, decisions, ideas, task cards and handoff, a short marked section in
`AGENTS.md`, and git hooks that check each commit and refresh the spreadsheet. It never overwrites a hook you
already have. Framework code never lives in your repository; upgrading Dev Charter upgrades every project that uses
it.

## What Dev Charter is not

- **Not a task tracker.** It does not replace Jira, Linear or ClickUp for scheduling work. It records what the
  product promises and whether each promise is kept.
- **Not a test framework.** It reads the results of the tests you already run.
- **Not tied to a language, stack or cloud.** Anything that can carry a comment and produce JUnit XML works.

## License

Apache License 2.0. See [LICENSE](https://github.com/joji-opensource/charter/blob/main/LICENSE) and
[NOTICE](https://github.com/joji-opensource/charter/blob/main/NOTICE).

If you redistribute Dev Charter or a modified version, keep the LICENSE file, the copyright notices and the NOTICE
file, as the License requires.
