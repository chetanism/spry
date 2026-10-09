---
title: Slicing
summary: How a ready story, task or bug becomes slices, and how each slice is opened, built and closed.
audience: 8
---
# Slicing

Run by `slice`, `slice-open` and `slice-close`. Tone: audience 8 — the person is a developer —
except a slice's `Summary`, which anyone on the team can read.

## When to stop and ask

A person decides three things, and the agent works through everything else without stopping:

- **The criteria** — a story goes `ready` only on a yes. They are what "done" means.
- **The merge** — `/spry:merge`, with what a person must accept (survivors, skipped controls,
  changed criteria) listed in its one ask.
- **Anything hard to undo** — a database migration, a public API or event shape, a new
  dependency, deleting data or files, or breaking a `Must not` rule.

Between them the checks stand in for a person watching: `spry.py gate` before close, every control
the diff adds falsified, a test's name citing each criterion, and `merge-check` blocking what is
missing. So open, build, test and close run as one piece of work.

## What a slice is

- **One reviewable change:** a reviewer reads it in one sitting.
- **One visible change:** its demo shows something that was not there before.
- Covers one or more acceptance criteria of **one** story; a story's criteria are all covered by
  its slices between them. A task's or bug's slices cover its `Done when` / the behaviour it fixes.
- Lives as `SL-<n>-<slug>.md` in its parent's folder. States: `planned` → `open` → `closed`
  (or `dropped`). `closed` is set in the pull request's last commit, so on the main branch it
  means merged.

## Split — `/spry:slice <story, task or bug>`

1. The parent must be `ready`. Unfinished `blocked_by` → say which, and ask whether to plan anyway.
2. Read the parent, its feature's rules, `spry/knowledge/conventions/INDEX.md`, decisions, and the
   code the change will touch.
3. Propose the slices in one reply: title, the criteria each covers, one line on the visible
   change. Order them so each builds on the last, and say which **need** an earlier one — its code,
   its data, its screen — and which could be built at the same time.
4. On approval, for each: `spry.py new slice --parent <ID> --title "…"`; fill only `Summary`,
   `covers`, and `blocked_by` with the earlier slices it needs — none when it only comes after one.
   The backlog lists a slice as ready only when those are closed, so two people never pick up a
   pair that cannot be built side by side. Everything else waits for `slice-open`.
5. `spry.py check`; commit `docs(plan): slices for <ID>`.

## Open — `/spry:slice-open [SL-n]`

No argument → offer the first row of *Ready to build* in `spry.py backlog`, and the next two as
alternatives.

1. **Read:** the parent and its feature, every knowledge file the change could touch (conventions,
   decisions, external behaviour, security, performance), and the code.
2. **Write the work order** — every `###` under `## Work order`:
   - `Summary` first: 2–4 bullets, readable by anyone — what will be done and what a person will see.
   - `Plan`: one bullet per file. `Must not`: the rules this could break, linked.
   - `Tests`: one per criterion at least, each name containing `<story>/AC-<n>`.
   - `Demo`: copy-pasteable; no value to fill in by hand.
3. **Conflict check** — `conflicts.md`, including open slices on the same files (`spry.py related`).
4. **Show the summary and the plan.** Ask to approve only when the plan does something hard to undo
   (*When to stop and ask*) or departs from the story; otherwise go on.
5. Then:
   - branch `sl-<n>-<slug>` from the main branch;
   - set `state: open`, `branch:`; `spry.py check`; commit `docs(slice): SL-<n> work order` —
     the branch's first commit, before any code;
   - push; open a **draft** pull request titled `SL-<n> <title>`, body from
     `spry.py pr-body SL-<n>`; set `pr:` to its number; commit and push.
6. **Build**, in this session, unless the person asked to open only. Then close.

## While building

- **Run `spry.py gate`**, not the test commands by hand. It runs `spry check`, then the fast checks
  (`checks.fast`: format, lint, types — cheapest first), then the affected tests, and stops at the
  first failure. A pass is stamped against the code; while only documents change it runs `check`
  alone. So fix lint before tests run, and write documents after the gate, never the reverse.
- **Never run the full suite** (`tests.all`). CI runs it on the main branch and nightly;
  `/spry:test-all` runs it when a person asks.
- **Push once,** at close. Each push runs CI again.
- **Never run `spry.py index` on a branch.** Generated blocks are written only by CI on the main
  branch; `check --base` refuses a branch that changed one, and `index --restore origin/<main>`
  puts them back. For fresh pages, `spry.py backlog`, `spry.py coverage`, or `spry.py view`
  (writes both to `.spry/view/`, never committed).
- A test that proves a criterion has `<story>/AC-<n>` in its name — the title string, docstring or
  parametrize id. A citation in a comment or in code proves nothing.
- A departure from the plan → note it for `What changed`; a new rule learned → `/spry:record` later.
- Never edit the work order to match the code after the fact; the close summary says what differed.

## Close — `/spry:slice-close [SL-n]`

1. **Gate:** working tree committed; `spry.py gate` passes. Otherwise fix what fails and run it
   again — it repeats only what the fix could change.
2. **What changed:** compare the diff (`git diff <main>...HEAD`) with `Plan`; write only the
   differences and why. Delete the section if none.
3. **Falsify** — prove the tests notice each safeguard the slice added:
   - `python3 spry/tool/spry.py falsify suggest SL-<n>` drafts `.spry/falsify/SL-<n>.json` from the
     source lines the branch added: one candidate per guard, comparison or error line, each with a
     mutation that removes it (a guard made *never true*, a boundary flipped, a `throw` deleted) and
     `expect` taken from `covers`.
   - **Keep every control the draft lists** — `merge-check` blocks when one has no row. Narrow
     each `expect` to the criteria that control serves, and add any the draft missed (same
     `find` / `with` form). A control that cannot run (it needs a clock, a network) gets the row
     `skipped — <reason>`, for a person to accept at the merge.
   - `falsify run .spry/falsify/SL-<n>.json --dry-run`, then
     `falsify run .spry/falsify/SL-<n>.json --record SL-<n>` — it runs only the tests citing each
     `expect`, stops at the first failure, restores every file, and writes the table. With
     `falsify.parallel` set (or `--jobs N`) it spreads controls over git worktrees and never
     touches this tree; commit first, or it runs serially and says why.
   - `survived` → a new test, then run again until `caught`. Only when no test should catch it,
     write the reason after `survived` in that row (`survived — logged only; no rule depends on it`):
     a person accepts it at the merge. A bare `survived` blocks the merge.
     `unreliable` → the baseline was red or timed out: fix that first.
4. **Proof:** every criterion in `covers` has a citing test, or tell QA which need a manual check
   (`[Test]` under `NEXT`).
5. **Follow-ups:** bugs, tasks, decisions found — create them (`spry.py new …`, `/spry:record`) and
   list their IDs.
6. Set `state: closed`; `spry.py gate` (only `check` runs — nothing but documents changed); commit
   `docs(slice): SL-<n> close summary` with the trailer `Slice: SL-<n>` in the body; push; replace
   the PR body with `spry.py pr-body SL-<n> --base origin/<main>`; mark the PR ready for review.
7. **Never merge here.** Tell the person the PR is ready for `/spry:review`, then `/spry:merge`.

## Slices side by side

Slices of stories that touch different files can be built at the same time, each in its own git
worktree and agent session:

- `spry.py related` on each work order, and the conflict check, show no shared file.
- `git worktree add ../<repo>-sl-<n> sl-<n>-<slug>`, then start a session there.
- Each worktree has its own `.spry/green`, so one gate never vouches for the other.
- They merge one at a time; the second rebases if the first touched anything it touches
  (`merging.md` step 5).
