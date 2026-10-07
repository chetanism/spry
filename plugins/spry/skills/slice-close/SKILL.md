---
name: slice-close
description: Close a slice — write its close summary from the diff, falsify the safeguards it added, confirm every criterion it covers is proven, record follow-ups, and mark the pull request ready for review. Never merges. Use when a slice's code is finished.
argument-hint: "[slice ID]"
---

# spry — slice-close

- **Procedure:** `spry/process/slicing.md` → *Close*. Read `chat.md` and `writing.md` beside it.
- **Slice:** `$ARGUMENTS`; without one, the `open` slice whose `branch` is the current branch.
- **Falsify carefully:** one mutation at a time, restore the file before the next, and confirm
  `git status` is clean at the end. A mutation left in place is the one unrecoverable mistake here.
- **Never merge** the pull request.
