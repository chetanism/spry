---
name: test-scenarios
description: Write the steps QA follows by hand to check each acceptance criterion of a story — with the data to use and what they should see — into the story's checks file. Use once a story is ready, before or while it is built.
argument-hint: "<story ID>"
---

# spry — test-scenarios

- **Procedure:** `spry/process/qa.md`. Read `chat.md` and `writing.md` beside it.
- **Template:** `spry/process/templates/checks.md` — audience 4.
- **Story:** `$ARGUMENTS`; without one, list ready stories with no `checks.md` and ask.
- Extend an existing `checks.md`; never rewrite or reorder its check log.
