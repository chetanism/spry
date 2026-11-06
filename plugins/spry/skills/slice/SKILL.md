---
name: slice
description: Split a ready story, task or bug into planned slices — each one reviewable in one sitting and showing one visible change — and record which acceptance criteria each covers. Use when a story is ready to be built.
argument-hint: "<story, task or bug ID>"
---

# spry — slice

- **Procedure:** `spry/process/slicing.md` → *What a slice is* and *Split*. Read `chat.md` beside it.
- **Parent:** `$ARGUMENTS`; without one, list ready stories, tasks and bugs that have no slices yet
  (`python3 spry/tool/spry.py status`) and ask.
- Every criterion of a story must be covered by its slices between them; say which slice covers each.
- A slice that needs an earlier one names it in `blocked_by`; one that merely comes after it does not.
- **With `slices.mode: steps`,** plan the story as steps and pack them into the fewest slices under
  `slices.steps` (`slicing.md` → *Steps*); each slice's file gets its `### Steps` headings and
  `Covers:` lines.
- Creates `planned` slices only, all in one `spry.py new slice` with a `--title` each — no branch,
  no code. `/spry:slice-open` comes next.
