---
name: bug
description: Record a bug against the feature or story it breaks — what happens, what should, how to reproduce it, its impact and severity — checked against open bugs for duplicates. Use when someone reports something not working as the plan says.
argument-hint: "[#issue] [feature or story ID] [what goes wrong]"
---

# spry — bug

- **Procedure:** `spry/process/planning.md` → *Bugs and tasks*. Read `interview.md`, `conflicts.md`
  and `chat.md` beside it.
- **Template:** `spry/process/templates/bug.md` — audience 4.
- **Parent:** from `$ARGUMENTS`, or find it: `spry.py related` on a draft, or ask which screen or
  story it is about. Create with `spry.py new bug --parent <ID> --title "<what goes wrong>"`.
  With `mint: main` it takes the ID on the main branch and merges it into this one — on a slice
  branch too.
- **From a GitHub issue** (`#<n>` in `$ARGUMENTS`): read it and its discussion first, and link the
  item to it — `planning.md` → *From a GitHub issue*.
- **`introduced_by`:** ask which slice's change brought the bug in, once. Write `SL-n` only on the
  person's answer; leave it empty when nobody knows. `spry pace` counts it against that slice.
- **Duplicates first:** read the open bugs under the same feature before writing anything.
