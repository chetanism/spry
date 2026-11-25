---
name: slice-plan
description: Plan a slice and stop: work order, design review, branch and draft PR, no code. Use to plan and build in separate sessions.
argument-hint: "[slice ID]"
---

# spry — slice-plan

1. **Slice:** `$ARGUMENTS`. None → `python3 spry/tool/spry.py backlog --section ready --rows 4 --plain`,
   and ask which row to plan: the first recommended with the next two as alternatives, or, with
   `slices.pick: ask`, the first four with none recommended.
2. **Claim, then read, in one call:**
   `python3 spry/tool/spry.py claim SL-<n> && python3 spry/tool/spry.py brief SL-<n> --as slice-plan`.
   The brief prints the slice, its parent and feature, what the conflict check starts from, and
   the procedure. A first line starting `!` → stop and do what it says.
3. **Follow the procedure it printed** — `slicing.md` → *Plan* — every step, in order. It is the
   only copy of the rules: nothing here repeats them.
4. **Write no code.** End after `spry.py publish SL-<n> open` with `[Run] /clear`, then
   `/spry:slice-build SL-<n>`.
