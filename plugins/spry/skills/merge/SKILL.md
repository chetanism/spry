---
name: merge
description: Merge a slice's pull request safely and report what is unblocked. Asks before merging. Use when the user says to merge a PR.
argument-hint: "[PR number or slice ID]"
---

# spry — merge

1. **Pull request:** `$ARGUMENTS`, or the current branch's. Never guess between two.
2. **Read, then start, in one call:**
   `python3 spry/tool/spry.py proc --for merge; python3 spry/tool/spry.py merge-ready <n>`.
   Checks pending → `merge-ready <n> --wait` in the background, never a polling loop. A
   `… this session carries` line → stop before the ask: `[Run] /clear`, then `/spry:merge <n>`.
3. **Follow the procedure it printed** — `merging.md` → *Merge* — every step, in order, every
   time. `merge-ready` runs steps 1–5 and prints the ask; on the yes, `spry.py merge-finish <n>`
   runs steps 7–8. By hand only for a PR no slice names.
4. **Never merge** a red or pending PR, without a yes for this PR in this conversation, or with
   `--admin`. A review's *fix, then merge* answer is that yes, unless the merge finds something
   the review did not report.
