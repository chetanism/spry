---
name: merge
description: Merge a slice's pull request safely — checks green, slice ready (merge-check), PR body current, approval, base not moved under it — then squash with the slice trailer, update the main branch, re-test only if it moved under the PR, write the progress tables when CI did not, and report what is unblocked. Asks before merging. Use when the user says to merge a PR.
argument-hint: "[PR number or slice ID]"
---

# spry — merge

- **Procedure:** `spry/process/merging.md` → *Merge* — every step, in order, every time. Read
  `chat.md` beside it.
- **Pull request:** `$ARGUMENTS`, or the current branch's. Never guess between two.
- **The tool runs the steps:** `spry.py merge-ready <n>` (steps 1–5, then the ask and the command),
  and on the yes `spry.py merge-finish <n>` (steps 7–8). By hand only for a PR no slice names.
  Checks pending → `merge-ready <n> --wait` in the background, never a polling loop.
- **Never merge** a red or pending PR, without a yes for this PR in this conversation, or with
  `--admin`. A review's *fix, then merge* answer is that yes, unless the merge finds something the
  review did not report.
- **CI that never ran** (no step started — billing, minutes, an outage) is neither green nor red:
  `merge-ready` runs the gate on the PR's head in its place, the person accepts that at the ask, and
  `merge-finish --ci-local "<reason>"` puts it in the commit.
- **After merging** `merge-finish` brings this tree to the main branch, waits for CI there only when
  the main branch moved under the PR, writes the progress tables when CI left them stale, syncs the
  request issues and names what is unblocked. Its `! … /spry:test-all` line means run the full suite
  once; its `[Test]` lines go to QA.
