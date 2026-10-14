---
title: Done
summary: Every finished story, task and bug, newest first, with the day its last slice closed.
audience: 3
---
# Done

What is finished, newest first: every story, task and bug whose slices are all closed — and, for a
story, whose criteria are all proven. *Closed* is the day its last slice closed; `—` means a slice
has no `closed:` date. CI on the main branch writes the block below with `spry index`; on any
branch, `python3 spry/tool/spry.py done` prints it. What is still to do is on [Backlog](BACKLOG.md).

<!-- spry:done -->
| # | Item | Type | Part of | Closed |
|--:|---|---|---|---|
| 1 | [T-1 Set up CI](plan/M-1-members-borrow-books/tasks/T-1-set-up-ci/README.md) | task | [M-1 Members can borrow books](plan/M-1-members-borrow-books/README.md) | 2026-09-18 |
<!-- /spry:done -->
