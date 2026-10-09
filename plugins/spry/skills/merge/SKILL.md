---
name: merge
description: Merge a slice's pull request safely — checks green, slice ready (merge-check), PR body current, approval, base not moved under it — then squash with the slice trailer, update the main branch, re-test only if it moved under the PR, and report what is unblocked. Asks before merging. Use when the user says to merge a PR.
argument-hint: "[PR number or slice ID]"
---

# spry — merge

- **Procedure:** `spry/process/merging.md` → *Merge* — every step, in order, every time. Read
  `chat.md` beside it.
- **Pull request:** `$ARGUMENTS`, or the current branch's. Never guess between two.
- **Never merge** a red or pending PR, without a yes for this PR in this conversation, or with
  `--admin`. A review's *fix, then merge* answer is that yes, unless the merge finds something the
  review did not report.
- **CI that never ran** (no step started — billing, minutes, an outage) is neither green nor red:
  the gate stands in for it on the PR's head, the person accepts that at the ask, and the commit
  says so (`merge-message --ci-local`).
- After merging, check whether the main branch moved under the PR (`spry.py changed --base <PR head>`):
  `code=false` → run nothing; `code=true` → wait for CI on the main branch, or with no CI on push,
  run the full suite once.
