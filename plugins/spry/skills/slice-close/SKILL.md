---
name: slice-close
description: Close a slice — rebase, write its close summary from the diff, confirm every criterion it covers is proven, record follow-ups, have it reviewed with fresh eyes and fix what is accepted, then falsify the safeguards it added, run the gate, and mark the pull request ready. Merges only through /spry:merge, on the review's answer. Use when a slice's code is finished.
argument-hint: "[slice ID]"
---

# spry — slice-close

- **Procedure:** `spry/process/slicing.md` → *Close*. Read `chat.md` and `writing.md` beside it.
- **Slice:** `$ARGUMENTS`; without one, the `open` slice whose `branch` is the current branch.
- **With an `issue:`,** post the close summary on it (`spry.py issue-body --close`); never edit its body.
- **Order:** rebase and the review come before falsify and the gate, so those run once, on the code
  that merges. Review fixes are checked with `spry.py gate --fast` only.
- **Falsify with the tool** (`spry.py falsify suggest`, then `run`) — never by editing files by hand;
  the tool restores every file, even when interrupted. Keep every control the draft lists.
  Confirm `git status` is clean afterwards.
- **Gate after falsify,** once, with the tool (`spry.py gate`), never by running test commands by hand,
  and never the full suite.
- **Follow-ups** are created with `spry.py new` (or `/spry:record`), never by copying a file and
  picking a number — with `mint: main` that takes the ID on the main branch.
- **Never merge** here — only `/spry:merge` merges; on the review's answer *a*, the close ends by
  running it.
