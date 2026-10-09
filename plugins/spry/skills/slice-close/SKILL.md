---
name: slice-close
description: Close a slice — write its close summary from the diff, falsify the safeguards it added, confirm every criterion it covers is proven, record follow-ups, and mark the pull request ready for review. Never merges. Use when a slice's code is finished.
argument-hint: "[slice ID]"
---

# spry — slice-close

- **Procedure:** `spry/process/slicing.md` → *Close*. Read `chat.md` and `writing.md` beside it.
- **Slice:** `$ARGUMENTS`; without one, the `open` slice whose `branch` is the current branch.
- **Gate with the tool** (`spry.py gate`), never by running test commands by hand, and never the
  full suite.
- **With an `issue:`,** post the close summary on it (`spry.py issue-body --close`); never edit its body.
- **Falsify with the tool** (`spry.py falsify suggest`, then `run`) — never by editing files by hand;
  the tool restores every file, even when interrupted. Keep every control the draft lists.
  Confirm `git status` is clean afterwards.
- **Never merge** the pull request.
