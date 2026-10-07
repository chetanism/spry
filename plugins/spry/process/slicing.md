---
title: Slicing
summary: How a ready story, task or bug becomes slices, and how each slice is opened, built and closed.
audience: 8
---
# Slicing

Run by `slice`, `slice-open` and `slice-close`. Tone: audience 8 — the person is a developer —
except a slice's `Summary`, which anyone on the team can read.

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
   change. Order them so each builds on the last.
4. On approval, for each: `spry.py new slice --parent <ID> --title "…"`; fill only `Summary` and
   `covers`. Everything else waits for `slice-open`.
5. `spry.py check`; commit `docs(plan): slices for <ID>`.

## Open — `/spry:slice-open [SL-n]`

No argument → offer the first `planned` slice whose parent's `blocked_by` are done, and the
alternatives.

1. **Read:** the parent and its feature, every knowledge file the change could touch (conventions,
   decisions, external behaviour, security, performance), and the code.
2. **Write the work order** — every `###` under `## Work order`:
   - `Summary` first: 2–4 bullets, readable by anyone — what will be done and what a person will see.
   - `Plan`: one bullet per file. `Must not`: the rules this could break, linked.
   - `Tests`: one per criterion at least, each name containing `<story>/AC-<n>`.
   - `Demo`: copy-pasteable; no value to fill in by hand.
3. **Conflict check** — `conflicts.md`, including open slices on the same files (`spry.py related`).
4. **Show the summary and the plan; ask to approve.** Nothing below happens without a yes.
5. On approval:
   - branch `sl-<n>-<slug>` from the main branch;
   - set `state: open`, `branch:`; `spry.py check`; commit `docs(slice): SL-<n> work order` —
     the branch's first commit, before any code;
   - push; open a **draft** pull request titled `SL-<n> <title>`, body from
     `spry.py pr-body SL-<n>`; set `pr:` to its number; commit and push.
6. **Stop.** Coding starts when the person says so, in this session or another.

## While building

- Run affected tests only (`tests.affected` in config); the full suite is for CI and close.
- A test that proves a criterion has `<story>/AC-<n>` in its name.
- A departure from the plan → note it for `What changed`; a new rule learned → `/spry:record` later.
- Never edit the work order to match the code after the fact; the close summary says what differed.

## Close — `/spry:slice-close [SL-n]`

1. **Gate:** working tree committed; affected tests and `spry.py check` pass. Otherwise stop and say
   what fails.
2. **What changed:** compare the diff (`git diff <main>...HEAD`) with `Plan`; write only the
   differences and why. Delete the section if none.
3. **Falsify** — prove the tests notice each safeguard the slice added:
   - `python3 spry/tool/spry.py falsify suggest SL-<n>` drafts `.spry/falsify/SL-<n>.json` from the
     source lines the branch added: one candidate per guard, comparison or error line, each with a
     mutation that removes it (a guard made *never true*, a boundary flipped, a `throw` deleted) and
     `expect` taken from `covers`.
   - Prune it with the person: keep the safeguards that matter; narrow each `expect` to the
     criteria that safeguard serves; add any the draft missed (same `find` / `with` form).
   - `falsify run .spry/falsify/SL-<n>.json --dry-run`, then
     `falsify run .spry/falsify/SL-<n>.json --record SL-<n>` — it runs only the tests citing each
     `expect`, stops at the first failure, restores every file, and writes the table. With
     `falsify.parallel` set (or `--jobs N`) it spreads controls over git worktrees and never
     touches this tree; commit first, or it runs serially and says why.
   - `survived` → a new test, then run again until `caught`; or write the reason after `survived`
     in that row (`survived — logged only; no rule depends on it`). A bare `survived` blocks the merge.
     `unreliable` → the baseline was red or timed out: fix that first.
4. **Proof:** every criterion in `covers` has a citing test, or tell QA which need a manual check
   (`[Test]` under `NEXT`).
5. **Follow-ups:** bugs, tasks, decisions found — create them (`spry.py new …`, `/spry:record`) and
   list their IDs.
6. Set `state: closed`; `spry.py check`; commit `docs(slice): SL-<n> close summary` with the
   trailer `Slice: SL-<n>` in the body; push; replace the PR body with `spry.py pr-body SL-<n>`;
   mark the PR ready for review.
7. **Never merge here.** Tell the person the PR is ready for `/spry:review`, then `/spry:merge`.
