---
name: review
description: Review with fresh eyes — a slice's PR against its work order, a plan PR or plan item against its parent, the code and the glossary, or any other PR — verify every finding, show them first, and on a yes post one inline comment per line with a suggested change wherever the fix is wording. COMMENT only on your own PR. One answer can also fix the accepted findings and merge, on your own PR; the reviewing agent itself never edits or merges. Use when a PR or a newly written plan item is ready for review, solo or on a team.
argument-hint: "[PR number, slice ID or plan item ID …]"
---

# spry — review

- **Procedure:** `spry/process/reviewing.md`. Read `chat.md` beside it.
- **Target:** `$ARGUMENTS` — PR numbers, `SL-n`, or plan item IDs — or the current branch's PR.
- **Fresh eyes:** a new agent reviews each target, never this session or a fork of it (§2).
- Verify every finding on its line before showing it; post only on a yes, after
  `spry.py review-check` prints `ready to post`.
- Ask 1 offers *post, fix, then merge* as one answer on your own PR; on that answer this session —
  never the reviewing agent — fixes exactly the accepted findings and runs `/spry:merge` (§5a).
- **The reviewing agent never** checks a branch out, pushes, edits code, approves without being told
  to, or merges.
