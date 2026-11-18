---
name: slice-plan
description: Plan a slice and stop — write its work order (starting with a short summary of what will be done), check it for conflicts, have a new agent review it and fix what is accepted, create the branch and a draft pull request, then stop before any code, so it can be built in a fresh session with /spry:slice-build. Use to plan with one model and build with another.
argument-hint: "[slice ID]"
---

# spry — slice-plan

- **Procedure:** `spry/process/slicing.md` → *When to stop and ask*, *What a slice is* and *Plan* —
  print only those: `python3 spry/tool/spry.py proc slicing "When to stop" "What a slice" Plan`,
  adding `Steps` for a slice with `### Steps`. Read `conflicts.md`, `chat.md` and `writing.md`
  beside it.
- **Slice:** `$ARGUMENTS`; without one, run `python3 spry/tool/spry.py backlog --section ready --rows 4 --plain` and ask which row
  of *Ready to build* to plan — the first recommended and the next two as alternatives, or, with
  `slices.pick: ask`, the first four with none recommended (`slicing.md` → *Plan*).
- **Brief:** `spry.py brief SL-<n> --as slice-plan` is the first read. When it says this session's
  context is past `slices.fresh_context`, stop and tell the person to `/clear` and run
  `/spry:slice-plan SL-<n>` (`slicing.md` → *Plan* step 1).
- **Claim first:** `spry.py claim SL-<n>` makes the branch — and with `mint: main` takes the slice
  on the main branch, or names who holds it (`slicing.md` → *IDs and claims*).
- **Write the plan for another session:** each `Plan` bullet says what changes in its file and the
  names and shapes it adds, so a smaller model can build it without this session (`slicing.md` →
  *Plan* step 2). A slice with `### Steps` gets each step's plan under its heading.
- **The design review always runs here**, whatever `slices.design_review` says: one new agent reads
  the finished work order, its findings are verified, accepted ones change the work order, and
  they are recorded under `### Design review`; a Blocker is asked first (`slicing.md` → *Plan*
  step 4).
- **The branch, the commit and the draft PR** are `spry.py publish SL-<n> open` — never `git commit`,
  `git push` and `gh pr create` by hand (`slicing.md` → *Plan* step 6).
- **Ask only** when the plan does something hard to undo, departs from the story, or the design
  review left a Blocker (`slicing.md` → *When to stop and ask*).
- **Write no code.** End after the publish with `[Run] /clear`, then `/spry:slice-build SL-<n>` —
  `/model` first to build on a smaller one.
