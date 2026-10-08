---
title: Testing beyond the slice
summary: The whole suite on purpose, and a seeded exploratory walk over a real instance — both report only, never fix.
audience: 8
---
# Testing beyond the slice

Run by `test-all` and `explore`. A slice runs only the tests its change affects; these two cover the
rest. **Both report; neither fixes.** A finding becomes a bug or task the person approves.

## Full suite

When a person asks, or after a change to dependencies or to build or test configuration — where
the affected-only run cannot tell what is affected. Never as a routine step of a slice or a
merge: CI runs the full suite on the main branch and nightly.

1. **Say what will run**, in one line: which parts, and whether the stack comes up. If the
   working tree has uncommitted changes, say so — the result is for the tree, not the last commit.
2. **Parts** come from `tests.parts` in config — `[{"name", "run", "stack"}]` — or, when absent,
   one part `all` running `tests.all`. A name given to the skill runs only that part.
3. **Cheapest first, timed each** (`time`), then:
   - `python3 spry/tool/spry.py check` first — a broken tree fails CI as surely as a red test;
   - before the first part with `"stack": true`: run `stack.running`. Already up → use it and
     leave it up. Not up → `stack.up`, and note that this run started it;
   - after the last part: `stack.down` — **only if this run started it, and always then**, even
     after a failure. Never remove volumes or data.
4. **Keep going after a failure**, so one run names every broken thing. Exception: a failed
   `stack.up` skips the parts that need it.
5. **Slowest:** `python3 spry/tool/spry.py tests --slowest --limit 5` when `tests.junit` is set;
   otherwise the runner's own summary.
6. **Report:**

   ```
   test-all — 4m 12s
   check        ok        2s
   unit         ok       41s
   integration  FAILED 3m 20s  2 of 164
     - <file> › <test name, with its S-n/AC-n>: <first line of the assertion>
   slowest
     38s  <file>
   ```

   - **A failure:** name it and say whether it looks like this branch or something older. Stop.
   - **Slow:** a part over 60s, or one file over a quarter of its part, is a finding.
   - **Flaky:** fails, then passes when that file alone is re-run once — a finding, never a pass.

Never: edit code or tests; skip, retry or quarantine to get green; stop a stack this run did not
start; leave one it did start running.

## Explore

A tester does three things a suite does not: combines steps nobody wrote down together, runs them
in an order nobody planned, and **notices**. This does that, seeded so a run can be replayed. It
does not re-assert what the tests assert; it covers what lies between slices.

### Rules

1. **The isolated instance, always.** Every shell starts by sourcing `explore.env`, which points
   ports and data away from the development instance. Without it, commands reach the instance
   being worked in, and nothing says so.
2. **Only `explore.up` / `explore.down` start or stop it.** Never the project's own dev commands.
3. **Report only.** Edit nothing in the repository, commit nothing, write no `checks.md` row. The
   transcript lives in `.spry/explore/<seed>/`.
4. **Predict before running.** A step with no written prediction is not a test.

### 1. Ready

- `explore.env`, `explore.up`, `explore.down` and `explore.fixture` in config, filled in. Any still
  `<…>` → stop, and fill them with the developer first. A half-set instance either fails at once
  or, worse, passes against the wrong data.

### 2. Ask

One message, three asks:

1. **Area** — the whole product, or a milestone, epic or feature (offer the broadest two or three).
2. **Depth:**
   | | Steps | Does |
   |---|---|---|
   | Sanity | ~15 | the main path plus four or five operators — is it broken right now |
   | Regular (recommended) | ~50 | operators across the area's criteria, evidence read back |
   | Deep | ~150 | every criterion in the area once, plus interrupt and concurrency |
   | Adversarial | ~300 | hostile, until it finds something or the budget ends |
3. **Seed** — new (`python3 spry/tool/spry.py draw --seed`), or replay a pasted one.

### 3. Bring it up

`explore.up` (with `--fresh` semantics for a replay: the data is reset first, or it is not a
replay), then `explore.fixture`. The fixture needs **two of everything that has a boundary** — two
organisations, two users with different roles — or the walk never tests isolation and passes for
the worst reason. Asynchronous work: poll with a bound, never sleep blind; reaching the bound is an
observation.

### 4. Walk

**Oracles** are the area's acceptance criteria — the stories under it, `ready` or done — plus the
rules in `spry/knowledge/security.md` and `performance.md`. They are kept true by `spry check`, so
a criterion can be trusted as written.

Each step, in order:

1. **Draw** an operator and a target:
   `printf '%s\n' <choices> | python3 spry/tool/spry.py draw <seed> <n> --pick`.
   Add 1 to `n` on **every** draw, including a redraw — two draws on one counter are one draw.
2. **Predict** the outcome and the criterion it comes from (`S-4/AC-2`). None fits → say so; the
   step is exploration, recorded as such, not as a pass.
3. **Run** it, with `explore.env` sourced.
4. **Judge:** match, or go to §5.
5. **Record** in `.spry/explore/<seed>/transcript.md`: counter, draw, prediction, command,
   observed, verdict.

- **Combine; don't repeat the suite.** Two- and three-step sequences, with state changing between.
- **Breadth first:** touch each criterion once before spending ten steps on one.
- **Don't clean up between steps.** Built-up state is the point.
- **Two at once** means `&` and `wait`, not two calls in a row.

Stop at the step budget, or when every criterion is touched and three steps in a row found
nothing. Say which.

### 5. Verify before reporting

**Assume the walk is wrong first.** On a mismatch: re-read the criterion and the documents it
rests on; reproduce on a fresh fixture with the shortest sequence (does not reproduce → `not
reproduced`, not a finding); then classify:

| | Means | Reported |
|---|---|---|
| defect | the code disagrees with a clear criterion | yes → offer `/spry:bug` |
| gap | the code is defensible and no criterion decides it | yes → ask who decides |
| walk error | the walk misread a criterion, the fixture, or an intended refusal | transcript only |
| expected | documented behaviour that only looks wrong | transcript only |

A repeated walk error means something is badly named — say so.

### 6. Report

- Chat rules apply. Every finding carries `seed:counter` — that pair is the whole reproduction.
- `FYI`: area, depth, steps, criteria touched and not reached, the transcript path.
- A finding worth re-checking later → offer a scenario in that story's `checks.md` via
  `/spry:test-scenarios`. Don't write it.
- Stop the servers; leave the instance up unless asked — `explore.down` when asked.

### Operators

| # | Operator | What must hold |
|---|---|---|
| 1 | Duplicate — send the same action twice | one effect, or a clear refusal of the second |
| 2 | Concurrent — two actors, same target, at once | one wins; no lost write, no half state |
| 3 | Reorder — a later step before an earlier one | refused, or the same end state |
| 4 | Delay — wait past an expiry, a cut-off, a slot | the time rule applies at the moment of acting |
| 5 | Skip — leave out a step the flow assumes | refused with a message naming what is missing |
| 6 | Substitute — another user's, organisation's or item's ID | refused; nothing about the other is revealed |
| 7 | Boundary — the limit, one below, one above | exactly the criterion's line |
| 8 | Malform — wrong type, empty, oversized, odd characters | refused at the edge, cleanly, nothing stored |
| 9 | Interrupt — stop mid-action (kill, timeout, disconnect) | all or nothing; a retry completes it once |
| 10 | Change underneath — edit or delete what a flow is using | the flow notices; no stale write |
| 11 | Repeat until the limit — hit a rate or quota | the limit holds and says so; recovery works |
| 12 | Clock — midnight, month end, time zones, daylight saving | dates land on the right day |
| 13 | Cross-boundary — act from one tenant or role on another | refused; even a suggestion is a leak |
| 14 | Read the evidence — logs, audit rows, queues, emails | each record exists, is right, leaks nothing |
