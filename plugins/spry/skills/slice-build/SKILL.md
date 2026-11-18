---
name: slice-build
description: Build a slice whose work order is already published — on its branch, to the plan, stopping to ask whenever the plan turns out wrong or short rather than guessing — then commit and stop, so it is closed in a fresh session with /spry:slice-close. Use after /spry:slice-plan, on whichever model the person chose to build with.
argument-hint: "[slice ID]"
---

# spry — slice-build

- **Procedure:** `spry/process/slicing.md` → *When to stop and ask*, *Build* and *While building* —
  print only those: `python3 spry/tool/spry.py proc slicing "When to stop" Build "While building"`,
  adding `Steps` for a slice with `### Steps`. Read `chat.md` beside it.
- **Slice:** `$ARGUMENTS`; without one, the `open` slice whose `branch` is the current branch.
- **Brief:** `spry.py brief SL-<n> --as slice-build` is the first read — the work order and the
  criteria in words. When it says this session's context is past `slices.fresh_context`, stop and
  tell the person to `/clear` and run `/spry:slice-build SL-<n>`. A slice still `planned` → stop:
  `/spry:slice-plan SL-<n>` comes first (`slicing.md` → *Build* step 0).
- **On the slice's branch,** never a new one (`slicing.md` → *Build* step 1).
- **The work order is the plan:** read what it names, build that. Never edit the work order.
- **A slice with `### Steps`** is built one step at a time: `spry.py step SL-<n>`, then
  `spry.py step SL-<n> --commit` — never `git commit` of code by hand (`slicing.md` → *Steps*).
- **Plan wrong or short → stop and ask**, saying what the plan says and what the code needs. Never
  fill a gap by guessing: the session that wrote the plan is gone (`slicing.md` → *Build* step 4).
  A detail no reviewer would weigh is noted for `What changed` and built.
- **Stop when built:** `spry.py gate --fast` green and every change committed, nothing pushed. End
  with `[Run] /clear`, then `/spry:slice-close SL-<n>` — `/model` first to close on a larger one.
  Never close here.
