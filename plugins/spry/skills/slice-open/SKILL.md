---
name: slice-open
description: Open a slice: write its work order, open the branch and draft PR, build it, and stop. Use when starting work on a slice.
argument-hint: "[slice ID]"
---

# spry — slice-open

1. **Slice:** `$ARGUMENTS`. None → `python3 spry/tool/spry.py backlog --section ready --rows 4 --plain`,
   and ask which row to open: the first recommended with the next two as alternatives, or, with
   `slices.pick: ask`, the first four with none recommended.
2. **Claim, then read, in one call:**
   `python3 spry/tool/spry.py claim SL-<n> && python3 spry/tool/spry.py brief SL-<n> --as slice-open`.
   The brief prints the slice, its parent and feature, what the conflict check starts from, and
   the procedure. A first line starting `!` → stop and do what it says.
3. **Follow the procedure it printed** — `slicing.md` → *Plan*, then *Build* — every step, in
   order. It is the only copy of the rules: nothing here repeats them. The person said to open
   only → stop where *Plan* does.
4. **Stop when built:** `spry.py gate --fast` green and everything committed, then `[Run] /clear`
   and `/spry:slice-close SL-<n>`. Never close in this session.
