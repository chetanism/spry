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
- **With `slices.issue` on,** the issue comes before the branch, from `spry.py issue-body`.
- **Ask only** when the plan does something hard to undo or departs from the story (`slicing.md` →
  *When to stop and ask*). Otherwise open the branch and the draft PR, build, and close — unless
  the person said to open only.
