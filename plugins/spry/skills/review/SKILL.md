---
name: review
description: Review a slice's PR, a plan item or any PR with a new agent; verify findings, show them, post on a yes. Use when one is ready for review.
argument-hint: "[PR number, slice ID or plan item ID …]"
---

# spry — review

- **Procedure:** `spry/process/reviewing.md`. Read `chat.md` beside it.
- **Target:** `$ARGUMENTS` — PR numbers, `SL-n`, or plan item IDs — or the current branch's PR.
- **Fresh eyes:** a new `spry:reviewer` agent reviews each target, never this session or a fork of it (§2). Its
  prompt holds the target and its kind, and no reasons; the agent knows how to start (§2).
- **A slice built in steps:** one new agent per step, given only that step's diff
  (`spry.py step SL-n --ranges`), and one for the seams between them (§3a).
- Verify every finding on its line before showing it; post only on a yes, after
  `spry.py review-check` prints `ready to post`.
- Ask 1 offers *post, fix, then merge* as one answer on your own PR; on that answer this session —
  never the reviewing agent — fixes exactly the accepted findings and runs `/spry:merge` (§5a).
- **The reviewing agent never** checks a branch out, pushes, edits code, approves without being told
  to, or merges.
