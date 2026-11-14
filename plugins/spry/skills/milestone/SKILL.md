---
name: milestone
description: Define one milestone with the product owner — why, done-when, scope and constraints — in plain words, then check it for conflicts. Does not define its epics. Use when planning the next big outcome.
argument-hint: "[#issue] [milestone ID to continue, or a title]"
---

# spry — milestone

- **Procedure:** `spry/process/planning.md`, at level **milestone**. Read it, and `interview.md`,
  `conflicts.md`, `chat.md` and `writing.md` beside it, before the first question.
- **Template:** `spry/process/templates/milestone.md` — its `audience` sets the tone of the document
  and of this conversation.
- No parent. Ask for the outcome in one sentence if `$ARGUMENTS` is empty; offer the roadmap's `Later` lines as candidates.
- Several milestones named at once → create their drafts in one `spry.py new` (`planning.md` §3),
  then define each in turn.
- **From a GitHub issue** (`#<n>` in `$ARGUMENTS`): read it and its discussion first, and link the
  item to it — `planning.md` → *From a GitHub issue*.
- **No spry here?** If `spry/spry.config.json` is missing, stop and offer `/spry:init` or
  `/spry:adopt`.
