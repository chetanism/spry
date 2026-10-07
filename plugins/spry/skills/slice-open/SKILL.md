---
name: slice-open
description: Open a slice — write its work order (starting with a short summary of what will be done), check it for conflicts with open slices and the project's rules, create the branch and a draft pull request, and stop before any code. Use when starting work on a slice.
argument-hint: "[slice ID]"
---

# spry — slice-open

- **Procedure:** `spry/process/slicing.md` → *What a slice is* and *Open*. Read `conflicts.md`,
  `chat.md` and `writing.md` beside it.
- **Slice:** `$ARGUMENTS`; without one, offer the first `planned` slice that is not blocked, and
  the alternatives.
- **Ask before** creating the branch, and **stop before any code** — even when the next step is obvious.
