---
name: slice-close
description: Close a slice: close summary, review, falsify, gate, PR ready. Use when a slice's code is finished.
argument-hint: "[slice ID]"
---

# spry — slice-close

1. **Slice:** `$ARGUMENTS`; none → the `open` slice whose `branch` is the current branch.
2. **Read, in one call:** `python3 spry/tool/spry.py brief SL-<n> --as slice-close` — the slice,
   what the branch changed, whether a rebase is due, and the procedure. A first line starting
   `!` → stop and do what it says.
3. **Follow the procedure it printed** — `slicing.md` → *Close* — every step, in order. It is the
   only copy of the rules: nothing here repeats them.
4. **Never merge** here — only `/spry:merge` merges; on the review's answer *a*, the close ends by
   running it.
