---
name: task
description: Record technical work no story asks for — set-up, upgrades, refactors — under the milestone or epic it serves.
argument-hint: "[#issue] [milestone or epic ID] [the work]"
---

# spry — task

- **Procedure:** `spry/process/planning.md` → *Bugs and tasks* — print only it: `python3 spry/tool/spry.py proc planning
  Bugs`, adding `"From a GitHub issue"` when planning from one. Read `interview.md`, `conflicts.md`
  and `chat.md` beside it.
- **Template:** `spry/process/templates/task.md` — audience 7.
- **Parent:** a milestone or epic, from `$ARGUMENTS` or asked. Create with
  `spry.py new task --parent <ID> --title "<the work>"`.
  With `mint: main` it takes the ID on the main branch and merges it into this one — on a slice
  branch too.
- **From a GitHub issue** (`#<n>` in `$ARGUMENTS`): read it and its discussion first, and link the
  item to it — `planning.md` → *From a GitHub issue*.
- **Is it really a task?** If a user would notice the result, offer `/spry:story` instead.
