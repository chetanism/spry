---
name: task
description: Record technical work no story asks for — set-up, upgrades, refactors, infrastructure — under the milestone or epic it serves, with why, what changes and how to tell it is done. Use when developers need work planned that is not a user-facing story.
argument-hint: "[milestone or epic ID] [the work]"
---

# spry — task

- **Procedure:** `spry/process/planning.md` → *Bugs and tasks*. Read `interview.md`, `conflicts.md`
  and `chat.md` beside it.
- **Template:** `spry/process/templates/task.md` — audience 7.
- **Parent:** a milestone or epic, from `$ARGUMENTS` or asked. Create with
  `spry.py new task --parent <ID> --title "<the work>"`.
- **Is it really a task?** If a user would notice the result, offer `/spry:story` instead.
