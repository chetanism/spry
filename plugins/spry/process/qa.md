---
title: Test scenarios
summary: How a story's acceptance criteria become the steps QA follows by hand, and how a manual check is logged.
audience: 6
---
# Test scenarios

Run by `test-scenarios`. Tone: audience 4 — the reader is QA: screens, fields, messages, nothing internal.

**A tester has what a user has.** For most products that is a browser and an account: no terminal,
no database, no server. A precondition the product cannot reach goes under *Before you start*,
addressed to whoever prepares the environment — never into a scenario.

## Write them

1. The story must be `ready`. Read it, its feature's rules, and its `Notes` (test data).
2. `python3 spry/tool/spry.py new checks --parent S-<n> --title x` creates `checks.md` from the
   template; an existing one is extended, never rewritten.
3. At least one `### AC-<n> · <short name>` per criterion that is not dropped, in order; a
   criterion may have several, and `### AC-1, AC-3 · …` checks both. `spry check` fails on a
   scenario for a criterion the story does not have.
4. **Read the list back first**, one line per scenario — its AC, Type and Ready (step 6) — and
   cut it with QA before writing any steps. A session nobody finishes is not coverage.
5. **Before you start**, first, when the scenarios need anything: *What is needed | Who provides it*
   — accounts and what each may do, data that must exist, equipment, a second browser — then the
   **Not through the screen** line, or no line when everything can be set up through the product.
   A tester who finds out three scenarios in that they needed a second account has lost the
   session. Scenarios that change data use their own, so they run in any order.
6. Each scenario starts with one line: `**Type** … · **Where** … · **Ready** …`.
   - **Type** — `happy path`, `negative`, `permission`, `another organisation`, `repeat`, `at
     once` or `boundary`. The ways somebody gets it wrong are most of what a session is for. When a
     story's criteria give only happy paths, ask its owner for the missing criterion; never write
     a case to a guess.
   - **Where** — the part of the product, as a person would say it; never a link or a route.
   - **Ready** — `yes`, or `no` and what it waits for (a story, a slice), so the scenario is written
     now and run the week it can be.
7. Then numbered steps, each `<what to do> → <what you should see>`, with the exact data to use;
   a step with nothing to check stops at what to do.
   - **Say what to achieve, not what to press.** *Lend the book to Kiran* survives a redesign;
     *press Lend* is wrong the week the button moves.
   - **What you should see** must be something you could be wrong about — never "it works". For a
     refusal, name what must **not** happen too: a refusal that half-saved the record is a bug.
   - Start from a state the tester can reach; never "assume". Each scenario stands on its own.
8. Add a scenario for a boundary only when the criterion has one ("3 books" → also try 2 and 4).
9. Read them back with QA; adjust; commit `docs(qa): scenarios for S-<n>`.

## Log a check

- One row per criterion per run in `## Check log`, appended, never edited:
  `| date | AC-n | build | who | pass / fail | notes |`.
- `build` is what was tested: a version, a commit, a deploy.
- A `fail` names the scenario and what happened in its notes; a result nobody can act on is no run.
- **The latest row for a criterion decides it.** A `fail` un-proves the criterion even where a test
  passes; record a bug (`/spry:bug`) and put its ID in the notes.
- **A criterion reworded under its scenarios:** `check --base` names each scenario and check-log row
  that relied on the old wording and is as it was where the branch started. Re-read them in the
  same PR: a scenario changed to fit is off the list, and a run of the criterion logged since the
  branch started takes them all off. A warning that stays is accepted at merge.
- `## Runs under writ`, in a project adopted from writ, is a record of runs before spry. It
  proves nothing and is never appended to.
