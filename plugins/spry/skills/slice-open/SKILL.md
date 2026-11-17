---
name: slice-open
description: Open a slice — write its work order (starting with a short summary of what will be done), check it for conflicts with open slices and the project's rules, create the branch and a draft pull request, then build it — asking first only when the plan does something hard to undo. Use when starting work on a slice.
argument-hint: "[slice ID]"
---

# spry — slice-open

- **Procedure:** `spry/process/slicing.md` → *What a slice is* and *Open*. Read `conflicts.md`,
  `chat.md` and `writing.md` beside it.
- **Slice:** `$ARGUMENTS`; without one, run `python3 spry/tool/spry.py backlog` and ask which row
  of *Ready to build* to open — the first recommended and the next two as alternatives, or, with
  `slices.pick: ask`, the first four with none recommended (`slicing.md` → *Open*).
- **Claim first:** `spry.py claim SL-<n>` makes the branch — and with `mint: main` takes the slice
  on the main branch, or names who holds it (`slicing.md` → *IDs and claims*).
- **A slice with `### Steps`** gets each step's plan under its heading, and is built one step at a
  time: `spry.py step SL-<n>`, then `spry.py step SL-<n> --commit` — never `git commit` of code by
  hand (`slicing.md` → *Steps*).
- **With `slices.design_review` on**, one new agent reads the finished work order before any code
  and its findings are recorded under `### Design review`; a Blocker is asked first (`slicing.md` →
  *Open* step 4).
- **The branch, the commits and the draft PR** are `spry.py publish SL-<n> open` — never `git commit`,
  `git push` and `gh pr create` by hand (`slicing.md` → *Open* step 6).
- **Ask only** when the plan does something hard to undo or departs from the story (`slicing.md` →
  *When to stop and ask*). Otherwise open the branch and the draft PR, build, and close — unless
  the person said to open only.
