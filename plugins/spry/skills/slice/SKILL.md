---
name: slice
description: Split a ready story, task or bug into planned slices, each covering named acceptance criteria. Use when a story is ready to be built.
argument-hint: "<story, task or bug ID>"
---

# spry — slice

- **Procedure:** `spry/process/slicing.md` → *What a slice is* and *Split* — print only those:
  `python3 spry/tool/spry.py proc slicing "What a slice" Split`. Read `chat.md` beside it.
- **Parent:** `$ARGUMENTS`; without one, list ready stories, tasks and bugs that have no slices yet
  (`python3 spry/tool/spry.py status`) and ask.
- Every criterion of a story must be covered by its slices between them; say which slice covers each.
- A slice that needs an earlier one names it in `blocked_by`; one that merely comes after it does not.
- Plan the story as steps and pack them into the fewest slices within `slices.steps`; each slice's
  file gets its `### Steps` headings and `Covers:` lines.
- Creates `planned` slices only, all in one `spry.py new slice` with a `--title` each — no branch,
  no code. `/spry:slice-open` comes next — or `/spry:slice-plan`, then `/spry:slice-build`, to
  build in a session of its own.
