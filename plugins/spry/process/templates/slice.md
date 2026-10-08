---
id: SL-<n>
title: <the change, in a few words>
state: planned
owner: <name>
audience: 8
covers: [<AC-1>]
branch: <sl-n-slug>
pr: <number, once opened>
blocked_by: []
related: []
---
# SL-<n> · <title>

<!-- guide: Reader: developers and the reviewer. Audience 8/10 — paths, types, commands are fine. Two parts: the Work order, written by /spry:slice-open before any code, and the Close summary, written by /spry:slice-close. This file is the source; the PR body is copied from it — the work order at open, both parts at close — and never edited by hand. Keep it to what a reviewer needs. -->

## Work order

### Summary

<!-- guide: 2–4 bullets, written at open. What will be done and what a person will be able to see afterwards. Readable by anyone on the team. -->

### Covers

<!-- guide: the parent's acceptance criteria this slice proves, as links — never restate their text. For a task or bug, its "Done when" lines. -->

### Plan

<!-- guide: one bullet per file: `path` — what changes. A code snippet only where the shape is not obvious (a signature, a query, a rule). -->

### Must not

<!-- guide: decisions, conventions, security or performance rules this change could break — as links, each with one line on how. Delete if none. -->

### Tests

<!-- guide: one bullet per test to add: test name (containing S-<n>/AC-<n>) — what it proves. -->

### Demo

<!-- guide: steps anybody can copy and paste or click through to see the change working. No values to substitute by hand. -->

### Conflict check

<!-- guide: written by the agent — spry/process/conflicts.md, including open slices touching the same files. -->

## Close summary

### What changed

<!-- guide: written at close, from the diff. Only where it differs from the plan, and why. Delete if it matches the plan. -->

### Falsify

<!-- guide: filled from `spry.py falsify`. Every control the draft lists keeps a row. A `survived` row needs a new test or a reason; a control that cannot run is `skipped — <reason>`. A person accepts each reason at the merge. -->

| Control | Mutation | Expect | Result |
|---|---|---|---|

### Follow-ups

<!-- guide: tasks, bugs or decisions created while doing this, with IDs. Delete if none. -->
