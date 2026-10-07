---
name: story
description: Write the stories of one feature with the product owner and QA — each with acceptance criteria a person can check — then check them for conflicts. Use when a feature is ready to be broken into stories.
argument-hint: "[parent ID] [title]"
---

# spry — story

- **Procedure:** `spry/process/planning.md`, at level **story**. Read it, and `interview.md`,
  `conflicts.md`, `chat.md` and `writing.md` beside it, before the first question.
- **Template:** `spry/process/templates/story.md` — its `audience` sets the tone of the document
  and of this conversation.
- Parent: a feature. Without one in `$ARGUMENTS`, list the ready features and ask.
- One run may write several stories; offer the list of story titles first, then do each in turn.
- Criteria rules: `planning.md` §4. Offer QA's view: "how would you check this by hand?"
- **No spry here?** If `spry/spry.config.json` is missing, stop and offer `/spry:init` or
  `/spry:adopt`.
