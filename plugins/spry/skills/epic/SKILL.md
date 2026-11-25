---
name: epic
description: Define one epic under a milestone with the product owner, in plain words. Does not define its features.
argument-hint: "[#issue] [parent ID] [title]"
---

# spry — epic

- **Procedure:** `spry/process/planning.md`, at level **epic**. Read it, and `interview.md`,
  `conflicts.md`, `chat.md` and `writing.md` beside it, before the first question.
- **Template:** `spry/process/templates/epic.md` — its `audience` sets the tone of the document
  and of this conversation.
- Parent: a milestone. Without one in `$ARGUMENTS`, list the milestones and ask.
- Several epics named at once → create their drafts in one `spry.py new` (`planning.md` §3),
  then define each in turn.
- **From a GitHub issue** (`#<n>` in `$ARGUMENTS`): read it and its discussion first, and link the
  item to it — `planning.md` → *From a GitHub issue*.
- **No spry here?** If `spry/spry.config.json` is missing, stop and offer `/spry:init` or
  `/spry:adopt`.
