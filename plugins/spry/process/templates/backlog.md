---
title: Backlog
summary: What is being built, what to build next, and what is still waiting for slicing, for other work or for planning.
audience: 4
---
# Backlog

What to pick up next, in plan order: milestone by milestone, bugs first, then tasks, then stories.
Nobody keeps this order by hand — it comes from the plan. CI on the main branch writes the block
below with `spry index`; on any branch, `python3 spry/tool/spry.py backlog` prints it, and
`python3 spry/tool/spry.py view` writes this page for your working tree to `.spry/view/`.
*Type* is story, task or bug — for a slice, what it builds. Built but not yet proven is on
[Coverage](COVERAGE.md); finished is on [Done](DONE.md).

<!-- spry:backlog -->
<!-- /spry:backlog -->
