---
name: bug
description: Record a bug against the feature or story it breaks — what happens, what should, how to reproduce it, its impact and severity — checked against open bugs for duplicates. Use when someone reports something not working as the plan says.
argument-hint: "[feature or story ID] [what goes wrong]"
---

# spry — bug

- **Procedure:** `spry/process/planning.md` → *Bugs and tasks*. Read `interview.md`, `conflicts.md`
  and `chat.md` beside it.
- **Template:** `spry/process/templates/bug.md` — audience 4.
- **Parent:** from `$ARGUMENTS`, or find it: `spry.py related` on a draft, or ask which screen or
  story it is about. Create with `spry.py new bug --parent <ID> --title "<what goes wrong>"`.
- **Duplicates first:** read the open bugs under the same feature before writing anything.
