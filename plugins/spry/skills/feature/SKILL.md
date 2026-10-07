---
name: feature
description: Define one feature with the product owner — how it works step by step and its numbered rules — in plain words, then check it for conflicts. Does not write its stories.
argument-hint: "[parent ID] [title]"
---

# spry — feature

- **Procedure:** `spry/process/planning.md`, at level **feature**. Read it, and `interview.md`,
  `conflicts.md`, `chat.md` and `writing.md` beside it, before the first question.
- **Template:** `spry/process/templates/feature.md` — its `audience` sets the tone of the document
  and of this conversation.
- Parent: an epic, or a milestone when `levels` has no epic. Without one in `$ARGUMENTS`, list them and ask.
- **Rules** are numbered `R-1…` so stories can cite them; one rule per line.
- **No spry here?** If `spry/spry.config.json` is missing, stop and offer `/spry:init` or
  `/spry:adopt`.
