---
name: slice-build
description: Build a slice whose work order is published, to the plan, then commit and stop. Use after /spry:slice-plan.
argument-hint: "[slice ID]"
---

# spry — slice-build

1. **Slice:** `$ARGUMENTS`; none → the `open` slice whose `branch` is the current branch.
2. **Read, in one call:** `python3 spry/tool/spry.py brief SL-<n> --as slice-build` — the work
   order, the criteria in words and the procedure. A first line starting `!` → stop and do what
   it says. A slice still `planned` → stop: `/spry:slice-plan SL-<n>` comes first.
3. **Follow the procedure it printed** — `slicing.md` → *Build* and *While building* — every step,
   in order. It is the only copy of the rules: nothing here repeats them.
4. **Stop when built:** `spry.py gate --fast` green and every change committed, nothing pushed.
   End with `[Run] /clear`, then `/spry:slice-close SL-<n>`. Never close here.
