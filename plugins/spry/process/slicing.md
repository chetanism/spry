---
title: Slicing
summary: How a ready story, task or bug becomes slices, and how each slice is opened, built and closed.
audience: 8
---
# Slicing

Run by `slice`, `slice-open`, `slice-plan`, `slice-build` and `slice-close`. Tone: audience 8 — the
person is a developer — except a slice's `Summary`, which anyone on the team can read.

## When to stop and ask

A person decides three things, and the agent works through everything else without stopping:

- **The criteria** — a story goes `ready` only on a yes. They are what "done" means.
- **The merge** — `/spry:merge`, with what a person must accept (survivors, skipped controls,
  changed criteria) listed in its one ask.
- **Anything hard to undo** — a database migration, a public API or event shape, a new
  dependency, deleting data or files, or breaking a `Must not` rule.

Between them the checks stand in for a person watching: `spry.py gate` at close, every control
the diff adds falsified, a test's name citing each criterion, and `merge-check` blocking what is
missing. So open, build, test and close run as one piece of work.

## What a slice is

- **One reviewable change:** a reviewer reads it in one sitting.
- **One visible change:** its demo shows something that was not there before.
- Covers one or more acceptance criteria of **one** story; a story's criteria are all covered by
  its slices between them. A task's or bug's slices cover its `Done when` / the behaviour it fixes.
- **Its `owner` is who builds it** — set at open, from the person git says is at this clone (their
  `team.members` name; solo, git's `user.name`), whoever planned it. `--owner <name>` names someone
  else. `merge-check` blocks a slice without one; `/spry:work-report` counts work by it.
- **Built in steps** with `slices.mode: steps`: one slice for as much of a story as fits the cap,
  each step its own commit and its own review — *Steps* below. A slice without steps is one step.
- Lives as `SL-<n>-<slug>.md` in its parent's folder. States: `planned` → `open` → `closed`
  (or `dropped`). `closed` is set in the pull request's last commit, so on the main branch it
  means merged.

## Split — `/spry:slice <story, task or bug>`

1. The parent must be `ready`. Unfinished `blocked_by` → say which, and ask whether to plan anyway.
2. Read the parent, its feature's rules, `spry/knowledge/conventions/INDEX.md`, decisions, and the
   code the change will touch.
3. Propose the slices in one reply: title, the criteria each covers, one line on the visible
   change. With `slices.mode: steps`, propose the same list as **steps**, then the slices that hold
   them (*Steps* → *Split*). Order them so each builds on the last, and say which **need** an earlier one — its code,
   its data, its screen — and which could be built at the same time.
4. On approval, all at once: `spry.py new slice --parent <ID> --title "…" --title "…"` — numbered in
   the order given; with `mint: main` it takes the numbers on the main branch in one push (*IDs and
   claims*), so the parent must be there. In each, fill only `Summary`, `covers`, and `blocked_by`
   with the earlier slices it needs — none when it only comes after one. A steps slice also gets its
   `### Steps` heading and each step's `#### Step <k> · <title>` with its `Covers:` line.
   The backlog lists a slice as ready only when those are closed, so two people never pick up a
   pair that cannot be built side by side. Everything else waits for `slice-plan` or `slice-open`.
5. `spry.py check`; commit `docs(plan): slices for <ID>`.

## Open — `/spry:slice-open [SL-n]`

*Plan*, then *Build*, in one session — for a person who builds with the model they plan with. The
design review runs only with `slices.design_review` on. Then stop, as *Build* ends: the close
starts in a fresh session. The person asked to open only → stop where *Plan* does.

## Plan — `/spry:slice-plan [SL-n]`

The work order, reviewed and published, and nothing else — so the person can build it in a session
of its own, with a smaller model if they like (`/spry:slice-build`), and close in another.

No argument → read *Ready to build* with `spry.py backlog --section ready --rows 4 --plain` — the
rows to choose from, without the rest of the backlog or its links' paths — and ask which slice to
open:

- `slices.pick: offer` (default) — the first row, recommended, and the next two as alternatives.
- `slices.pick: ask` — the first four rows, none recommended: the order is the plan's and the
  dependencies', and what else bears on the choice (a design not settled, an outside team's date) is
  the person's. The one exception to `chat.md`'s single `(recommended)`.

0. **Claim it:** `spry.py claim SL-<n>` — before anything else, so nobody spends an hour on a work
   order someone else is writing. With `mint: main` it sets the slice's `branch:` and `owner:` on
   the main branch and pushes; refused when someone
   holds it, naming the branch — then offer the next ready row. Either way it makes the branch
   `sl-<n>-<slug>` and switches to it. Not opened after all → `spry.py release SL-<n>`.
1. **Read:** `spry.py brief SL-<n> --as <skill>` first (`<skill>` is the one running, `slice-plan`
   or `slice-open`) — one call for the slice, the criteria it covers, its parent and feature, what
   the conflict check starts from, and this procedure. Do not open those again. When it says the
   session's context is past `slices.fresh_context`, stop: `[Run] /clear`, then that skill again.
   Then every knowledge file the change could touch (conventions, decisions, external behaviour,
   security, performance) and the code — the files you already know you need in one call.
2. **Write the work order** — every `###` under `## Work order`:
   - `Summary` first: 2–4 bullets, readable by anyone — what will be done and what a person will see.
   - `Plan`: one bullet per file, concrete enough to build without this session — what changes in
     it, the names and shapes it adds — since the build may run in another session, on a smaller
     model. `Must not`: the rules this could break, linked. A steps slice has
     no `Plan`: each step under `### Steps` gets its plan bullets (*Steps* → *Work order*).
   - `Tests`: one per criterion at least, each name containing `<story>/AC-<n>`.
   - `Demo`: copy-pasteable; no value to fill in by hand.
3. **Conflict check** — `conflicts.md`, from the brief's *Related*; once the `Plan` names its
   files, `spry.py related <slice file>` again for open slices on the same ones.
4. **Design review** — always under `slice-plan`; under `slice-open` only with
   `slices.design_review` on. A plan another session builds from gets its second reading here or
   nowhere. The review at close asks whether the
   code is what the work order said; this one asks whether the work order is right, while changing
   it costs nothing.
   - **One new agent** — the `spry:reviewer` agent in Claude Code — never a fork of this session, given only: the slice file, its parent and
     the parent's feature, `AGENTS.md`, the decisions and conventions indexes, and the four checks
     below. It may read the code; it edits nothing. Leave out why the plan is as it is.
   - It checks:
     1. each choice the plan makes without asking — is it truly easy to undo (*When to stop and
        ask*)? A data model, an API or event shape, a module boundary, who owns a record, what
        happens on failure;
     2. what the plan assumes that no story, feature or decision says;
     3. for each such choice, an option harder to build and better for the product;
     4. in a steps slice, what each step needs from an earlier one, and whether the plan names it.
   - It reports **Blocker** (hard to undo, and not asked), **Should** or **Nit**, each with the
     line of the work order it rests on.
   - **Verify each finding** against the plan and the code; drop what does not hold. A Blocker
     that stands becomes an ask in step 5, before any code. An accepted Should changes the work
     order now.
   - Record it as the work order's last section, `### Design review`: `- <n> Blocker, <n> Should —
     <n> asked` — the findings that stood, and how many went to the person — then one line for
     each Blocker and its answer. `merge-check` warns when the section is missing or a Blocker
     went unasked; `spry pace` shows the counts.
5. **Show the summary and the plan.** Ask to approve only when the plan does something hard to undo
   (*When to stop and ask*), departs from the story, or the design review left a Blocker; otherwise
   go on.
6. Then `spry.py publish SL-<n> open` (`--owner <name>` when building it for someone else). It
   sets `state: open`, `branch:` and `owner:`; refuses, changing nothing, when `check` does; commits
   `docs(slice): SL-<n> work order` — the branch's first commit, before any code; pushes; opens a
   **draft** pull request titled `SL-<n> <title>` with the body from `pr-body`; and links, commits
   and pushes its number. It commits only files under `spry/`, and refuses while code is uncommitted.
7. **Stop.** Under `slice-plan`: `[Run] /clear`, then `/spry:slice-build SL-<n>` — `/model` first
   to build on a smaller one; the work order is the hand-off. Under `slice-open`: *Build* from its
   step 2, in this session.

## Build — `/spry:slice-build [SL-n]`

The code for a work order already published — by `/spry:slice-plan`, or by an open stopped early.
Run on whichever model the person chose; the work order holds what this session needs.

0. **Brief:** `spry.py brief SL-<n> --as slice-build` (no ID → the `open` slice whose `branch` is the
   current branch). Past `slices.fresh_context` → stop: `[Run] /clear`, then
   `/spry:slice-build SL-<n>`. A slice still `planned`, or with no `## Work order` → stop:
   `/spry:slice-plan SL-<n>` comes first.
1. **Branch:** on the slice's `branch:` — `git fetch`, then `git switch <branch>`. Checked out in
   another worktree → build there (`/spry:worktree`). Never a new branch.
2. **Read** what the work order names: the files in `Plan` (or the step's plan), the rules linked
   under `Must not`, the `### Design review` answers — in one call. The brief's *Rules that failed
   the checks most* are the lint and type rules this project's code keeps breaking: write to them. Not the planning again: the parent, the
   feature and the knowledge indexes were read when the plan was written.
3. **Build** to the plan, as *While building* says; a steps slice one step at a time (*Steps* →
   *Build*).
4. **The work order turns out wrong or short** — a file it names does not fit, a test cannot be
   written as planned, the change needs a shape or a file the plan does not name → stop and ask,
   with what the plan says and what the code needs. The session that wrote the plan, and its
   reasons, are gone, so a gap is never filled by guessing. A detail no reviewer would weigh — a
   helper, a local name — is noted for `What changed` and built.
5. **Stop** when the plan is built: `spry.py gate --fast` passes and every change is committed —
   not pushed (*While building*). Then `[Run] /clear`, then `/spry:slice-close SL-<n>` — `/model`
   first to close on a larger one. The slice file and the commits are the hand-off; a close that
   carried the build would read it again on every request (*Close* step 0).

## While building

- **Every request reads the whole session again.** The cost of a step is the session's size times
  the requests it takes, so take fewer:
  - Independent reads and commands go in one call (`a; b; c`) or in parallel calls, never one by
    one.
  - Read only the part of a file or an output you need (`sed -n`, `grep -n`), never a whole log.
  - Let the tool wait (`gate` in the background, `merge-ready --wait`), never a polling loop.
  - `spry.py brief SL-<n> --as <skill>` gives the slice, what its skill reads first and this
    procedure in one call; `proc --for <skill>` the procedure alone; `backlog --section … --rows …
    --plain` only the rows needed.
- **A slice built in steps** is built one step at a time and never committed by hand — *Steps* →
  *Build*.
- **Check each change with `spry.py gate --fast`:** `spry check`, then the fast checks
  (`checks.fast`: format, lint, types — cheapest first), no tests. `spry.py gate` adds the affected
  tests — run it when a test's answer is what you need, not on every change: it costs minutes on a
  big project, and it runs once more at close, after the review, on the code that merges. Run the
  full gate in the background and tell the person how long it usually takes: it prints that first,
  then each step as it starts (`→ affected tests · usually 3m20s`) and ends.
- **The tool is the proof**, not the test commands by hand. The fast checks all run and the tests
  wait for them; a failing test step stops the gate. A full pass is stamped against the code; while
  only documents change it runs `check` alone. So fix lint before tests run, and write documents
  after the gate, never the reverse. With `tests.retry` set, affected tests that fail on a timeout
  run once more, quietly; a real failure fails both runs, so never re-run the gate to get past a
  timeout.
- **After a red gate read it, do not run it again.** Never cut the gate's output with `tail`, `head`
  or `grep`: its last line names the failing test files and `.spry/gate/last.log`, which holds the
  rest. Fix, rerun just those tests with `spry.py gate --failed`, and run the full gate once. On
  unchanged code the gate shows the last failure instead of running again; `--force` is for a flaky
  test or a busy machine.
- **Never run the full suite** (`tests.all`). CI runs it on the main branch and nightly;
  `/spry:test-all` runs it when a person asks.
- **Push only at close:** once for the review, once when it ends. Each push runs CI again.
- **Never run `spry.py index` on a branch.** Generated blocks are written only on the main branch —
  by CI, or by `/spry:merge` when CI left them stale (`merging.md` step 8); `check --base` refuses a
  branch that changed one, and `index --restore origin/<main>` puts them back. For fresh pages,
  `spry.py backlog`, `spry.py coverage`, or `spry.py view` (writes both to `.spry/view/`, never
  committed); `spry.py serve` shows them, and the whole plan, in a browser.
- A test that proves a criterion has `<story>/AC-<n>` in its name — the title string, docstring or
  parametrize id. A citation in a comment or in code proves nothing.
- A departure from the plan → note it for `What changed`; a new rule learned → `/spry:record` later.
- Never edit the work order to match the code after the fact; the close summary says what differed.

## Close — `/spry:slice-close [SL-n]`

The review comes first and the slow proof last, so falsify and the gate each run once, on the code
that merges.

0. **Brief:** `spry.py brief SL-<n> --as slice-close` — the slice, what the branch changed, and
   under *Before the close* whether the tree is committed and the main branch has moved. When it
   says the session's context is past `slices.fresh_context`, stop: `[Run] /clear`, then
   `/spry:slice-close SL-<n>`.
1. **Rebase:** working tree committed; when the brief says `origin/<main>` has moved, rebase onto
   it — a rebase after the gate means a second gate. `spry.py gate --fast` passes.
2. **What changed:** compare the diff (`git diff <main>...HEAD`) with `Plan` (a steps slice: each
   step's plan under `### Steps`); write only the
   differences and why. Delete the section if none.
3. **Proof:** every criterion in `covers` has a citing test, or tell QA which need a manual check
   (`[Test]` under `NEXT`).
4. **Follow-ups:** bugs, tasks, decisions found — create them (`spry.py new …`, `/spry:record`) and
   list their IDs. With `mint: main` each number is taken on the main branch and the main branch is
   merged into this one, so the ID is final at once: cite it anywhere.
5. **Review:** `spry.py publish SL-<n> review` — commits the close notes under `spry/`, pushes
   (`--force-with-lease`, so step 1's rebase goes up), and replaces the PR body with
   `pr-body --base origin/<main>`; the PR stays a draft. Code is committed first, as it was built.
   `/spry:review SL-<n>`, and the fixes accepted applied (`reviewing.md` §5a)
   — before falsify and the gate, so a fix costs neither a second time. A steps slice gets one
   reviewer per step and one for the seams; each fix is a fixup of its step (*Steps* → *Close*). The review reads no
   Falsify rows yet; `merge-check` and the merge's ask cover them. The close waits for the review's
   Ask 1; on *c* or *d* it goes on to *Falsify* with nothing fixed.
   - **Record it** under `### Review` in the close summary: `- <n> Blocker, <n> Should, <n> Nit —
     <n> fixed` — the findings that stood once verified, every reviewer of a steps slice counted
     together, and how many were fixed. Another review after the fixes adds its own line.
     `spry pace` reads the counts; `merge-check` shows them.
6. **Falsify** — prove the tests notice each safeguard the slice added. The tool says what each
   other case needs as it meets it — a control to write by hand, one no test names, a wide one,
   `survived`, `unreliable`, a slot left out, a row kept from an earlier run: do what it prints.
   - `python3 spry/tool/spry.py falsify suggest SL-<n>` drafts `.spry/falsify/SL-<n>.json`: one
     control per source line the branch added that refuses, stops or decides, each with the
     mutation that removes it and `expect` from `covers` (a bug's or a task's slice: its ID).
     No source line added → it says so, and there is nothing to falsify.
   - **Keep every control the draft lists.** Narrow each `expect` to the criteria that control
     serves, and add any the draft missed (same `find` / `with` form). A guard covered by a test
     no ID names takes that test file's path as its `expect`. A control that cannot run (a clock,
     a network) gets the row `skipped — <reason>`, for a person to accept at the merge.
   - A `control` may be renamed in plain words; keep the `<!-- f:… -->` in its row.
   - `falsify run .spry/falsify/SL-<n>.json --dry-run`, then the same with `--record SL-<n>` — it
     runs each control's tests, restores every file, and writes the table. Commit first: with
     `falsify.parallel` it runs in worktrees of its own.
   - `survived` → a new test, then run again until `caught`. Only when no test should catch it,
     write the reason after `survived` in that row (`survived — logged only; no rule depends on
     it`). A bare `survived` blocks the merge.
   - Falsify comes after the review and before the gate, and needs no gate first: it runs its own
     baseline.
7. **Gate:** working tree committed, falsify's new tests included — in a steps slice, as fixups,
   folded in first with `spry.py step SL-<n> --squash`; `spry.py gate` passes. Otherwise
   fix what fails and run it again — it repeats only what the fix could change. A branch that
   changed only test files runs just those, then `tests.always`, and says so on its first line;
   it stamps green like any pass. A changed integration test runs too, so start its services first.
8. `spry.py publish SL-<n> ready` — sets `state: closed` and `closed: <today>` (the Done page dates
   the item by it, and `merge-check` blocks without it); runs the gate (only `check` runs — nothing
   but documents changed), and on red puts the slice back to open and commits nothing; commits
   `docs(slice): SL-<n> close summary` with the trailer `Slice: SL-<n>`; pushes; replaces the PR body
   with `pr-body --base origin/<main>`; and marks the PR ready for review.
   A slice gets no GitHub issue: the request issues its story, bug or task came from follow the
   plan through `spry.py issues --sync` (`planning.md` → *From a GitHub issue*).
9. **Merge only through `/spry:merge`.** The review is done (step 5): on its answer *a*, run
   `/spry:merge` now; otherwise tell the person the PR is ready for it. A teammate may still review
   the ready PR.

## Steps — `slices.mode: steps`

For a project that wants a story's fixed costs — the work order, the review set-up, falsify, the
full gate, CI, the merge — paid once rather than once per slice, with no less review or proof. The
agent still builds one thing at a time and each reviewer still reads one thing; the tool, not this
file, keeps that so (DESIGN.md §15 *Steps mode*).

- **Split.** Plan the story as steps exactly as you would plan slices — a title, the criteria each
  covers, one visible change each, in build order, `—` for a step that only prepares. Then pack
  consecutive steps into the **fewest slices** that keep to `slices.steps.max` (default 5 steps)
  and, by your estimate, `slices.steps.max_lines` (default 800 changed lines, documents and
  `checks.generated` files not counted; `0` is no slice cap). With `slices.steps.step_lines` set
  (default `0`, off), also estimate each step against it, and split a step you expect to be over.
  Steps that two people could build at the same time go into different slices. A story that fits
  is one slice.
- **Work order.** `### Steps` replaces `### Plan`:

  ```markdown
  ### Steps

  #### Step 1 · Refuse a fifth book

  Covers: AC-1

  - `src/lend.ts` — `lend` returns `AtLimit` at the limit
  ```

  `check` refuses steps not numbered from 1, more than `slices.steps.max`, a step without `Covers:`,
  a criterion a step names that the slice's `covers` does not, and one the slice covers that no
  step does. `Tests` and `Demo` stay whole-slice.
- **Build.** `spry.py step SL-<n>` names the next step and its plan, from the commits already made
  — so a new session, or one after a compaction, starts there. Build that step only, then
  `spry.py step SL-<n> --commit`: `gate --fast`, then one commit, `SL-<n> step <k>: <title>`, with
  the trailer `Step: SL-<n>/<k>`. A `!` after the commit saying the session is past
  `slices.fresh_context` → stop there: `[Run] /clear`, then `/spry:slice-build SL-<n>`, which
  starts at the next step — every request of the steps left would read the steps built again. A step over `slices.steps.step_lines` is a `!` after the commit:
  split it now (`git reset --soft HEAD^`, then commit its parts as steps) or leave it for the person
  to accept at the merge. It runs every `fix` in `checks.fast` (the
  formatter) on the step's files first and says which changed, so never format by hand. Red fast
  checks → fix and run it again. With `slices.steps.tests`
  on, it also runs the test files the step added or changed (not those in
  `slices.steps.tests_skip`), and a red one refuses the commit and names the file: fix it in this
  step, not at close. **Never `git commit` code
  by hand** on a steps branch; the `step_commit` hook refuses it. Documents — the work order, the
  close summary — are committed as usual. The affected tests run only when their answer is needed
  (`spry.py gate`), as in any slice.
- **Close.** As *Close* above, with three differences:
  - **Review** (step 5): `/spry:review SL-<n>` starts one reviewer per step and one for the seams
    (`reviewing.md` §3a). `spry.py step SL-<n> --ranges` gives each one its diff, from any branch.
  - **Fixes and falsify's new tests** are `git commit --fixup=<the step's commit>` — the step the
    code belongs to; never `--squash`, whose message would bury the step's trailer. Nothing but
    documents is committed until the gate.
  - **Before the gate** (step 7): commit the Falsify table, then `spry.py step SL-<n> --squash`
    folds the fixups into their steps. Every step is one clean commit again, for a person who reads
    the PR commit by commit. Step 8's push is `git push --force-with-lease`, so CI still runs twice.
    With `mint: main` the main branch may have been merged in at step 4; when `--squash` stops on
    that merge, rebase onto `origin/<main>` and run it again.
- **Merge.** `merge-check` blocks a step with no commit, one committed twice or out of order, code
  committed without a trailer, and a fixup not folded in. A slice over `slices.steps.max_lines`,
  and each step over `slices.steps.step_lines`, is a `!` the person accepts; generated lines (`checks.generated`) are printed beside the size,
  not counted in it. The squash keeps the step titles in its body.

## Slices side by side

Slices of stories that touch different files can be built at the same time, each in its own git
worktree and agent session:

- `spry.py related` on each work order, and the conflict check, show no shared file.
- With a `worktrees` block, `/spry:worktree` gives the session one (*Worktrees*, below); without,
  `spry.py claim SL-<n> --no-switch`, then `git worktree add ../<repo>-sl-<n> sl-<n>-<slug>`, and
  start a session there.
- Each worktree has its own `.spry/green`, so one gate never vouches for the other.
- With `checks.lock: true`, gates and falsify runs in different worktrees run one after the
  other: a run that waits prints who holds the lock, then goes on. Do not stop or retry it.
- They merge one at a time; the second rebases if the first touched anything it touches
  (`merging.md` step 5).

## Worktrees

With a `worktrees` block in the config, spry makes the worktrees and hands them out
(`/spry:worktree`, `spry.py worktree`):

```json
"worktrees": {"dir": ".claude/worktrees", "home_branch": "alt{index}", "max": 4,
              "setup": "tooling/worktree-setup.sh", "share": [".env.example"], "stale_after": 12}
```

- **`setup`** runs once in a new worktree with `SPRY_WORKTREE` (its index) and `SPRY_WORKTREE_NAME`
  set. It creates what the project isolates: a database, ports, its `.env`. Falsify slots run it
  too, with `SPRY_FALSIFY_SLOT` also set and `SPRY_WORKTREE` the index of the tree the run is in
  (0 in the main checkout), in place of `falsify.setup`.
- **A session never enters a worktree another session has claimed.** `worktree claim` refuses one a
  live session holds; a claim whose process is gone, or that wrote nothing for `stale_after` hours,
  is taken and said. The session-end hook releases it.
- **A worktree rests on its home branch at the main branch's head between slices.** `/spry:merge`
  sends it there (`worktree home`) after the squash, in place of checking out the main branch,
  which the main checkout holds.
- The main checkout is never claimed: plan-only sessions share it.
- **Progress:** `step --commit`, `gate`, `falsify run`, `review-check`, `merge-check` and
  `worktree home` each write one line to the main checkout's `.spry/progress/events.jsonl`;
  `spry.py watch` draws a panel per worktree from it. Inside a long step, `spry.py say "<text>"`
  adds a milestone — always alongside the next tool call, never as a turn of its own.
- `worktree prune` removes falsify's scratch trees an interrupted run left, and the records of
  worktrees deleted by hand.

## IDs and claims

Several sessions, or several people, work on one repository at once. `mint` in config says where
an ID is taken and a slice is claimed:

- **`main`** — the main branch on the remote is the counter, and the push is the lock. `spry.py new`
  (with an ID) fetches it, numbers the item from the file names on `origin/<main>`, checks the new
  file, commits `docs(plan): new <ID> <title>` on that tip and pushes there; a push refused because
  someone pushed first fetches and tries again, up to five times. Several items in one `new` are
  one commit and one push, and a retry renumbers them all. Then it merges that commit into the
  current branch — the file is there to fill, and the merge base holds it, so the branch's edits
  never meet the main branch's copy as a second addition. `claim` does the same with `branch:`,
  reading the slice as the main branch has it, and refuses when a branch for it already exists here
  or on the remote. Offline, a push refused for any other reason, files staged, or a merge in
  progress → it stops and writes nothing; it never falls back to a local number. Nothing is checked
  out and no other plan file is opened, so it costs the fetch and the push.
- **`local`** — the next number in this tree, as before. For a main branch that takes no direct
  commit. Two branches can take the same number; `check --base origin/<main>` names it before the
  merge, and the later branch renames.
- **`spry.py release SL-<n>`** gives back a slice nobody is building: `planned` again, `branch:`
  empty. The branch itself is left for its owner to delete.
- The backlog's *In progress* lists a claimed slice (a `planned` slice with a `branch:`), and
  `related` lists it among open slices, whoever claimed it.
