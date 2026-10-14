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
### In progress

Being built now — open, or on a branch named for the slice. Leave these to their owner.

| # | Slice | Type | Part of | Owner | Where | Unblocks |
|--:|---|---|---|---|---|---|
| 1 | [SL-2 Refuse a loan over the limit](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/S-2-loan-limit/SL-2-refuse-over-limit.md) | story | [M-1 Members can borrow books](plan/M-1-members-borrow-books/README.md) › [E-1 Lending](plan/M-1-members-borrow-books/E-1-lending/README.md) › [F-1 Lend at the desk](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/README.md) › [S-2 Loan limit](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/S-2-loan-limit/README.md) | Ravi | `sl-2-refuse-over-limit` · PR #14 | — |

### Ready to build

Planned, and nothing they wait for is unfinished. The first row is next; `/spry:slice-open` with no ID offers it. *Unblocks* is what waits on the slice, or on something it is part of — between two rows, the one that frees more.

| # | Slice | Type | Part of | Covers | Owner | Unblocks |
|--:|---|---|---|---|---|---|
| 1 | [SL-4 Due date in the library's time zone](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/bugs/B-1-due-date-a-day-early/SL-4-due-date-in-library-time-zone.md) | bug | [M-1 Members can borrow books](plan/M-1-members-borrow-books/README.md) › [E-1 Lending](plan/M-1-members-borrow-books/E-1-lending/README.md) › [F-1 Lend at the desk](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/README.md) › [B-1 Due date a day early on evening receipts](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/bugs/B-1-due-date-a-day-early/README.md) | — | Ravi | [SL-5 Correct due dates on loans already made](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/bugs/B-1-due-date-a-day-early/SL-5-correct-loans-already-made.md) |

### Needs slicing

Ready, but no slice is planned for all of it yet — `/spry:slice <ID>` splits it.

_None._

### Blocked

Waiting on unfinished work, named here with where it stands and who owns it.

| # | Item | Type | Part of | Waiting on | Owner |
|--:|---|---|---|---|---|
| 1 | [SL-5 Correct due dates on loans already made](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/bugs/B-1-due-date-a-day-early/SL-5-correct-loans-already-made.md) | bug | [M-1 Members can borrow books](plan/M-1-members-borrow-books/README.md) › [E-1 Lending](plan/M-1-members-borrow-books/E-1-lending/README.md) › [F-1 Lend at the desk](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/README.md) › [B-1 Due date a day early on evening receipts](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/bugs/B-1-due-date-a-day-early/README.md) | [SL-4 Due date in the library's time zone](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/bugs/B-1-due-date-a-day-early/SL-4-due-date-in-library-time-zone.md) · ready to build (Ravi) | Ravi |

### Needs planning

Product's next step: finish a draft, or add what an item is still missing.

| # | Item | Type | Part of | Needs | Owner |
|--:|---|---|---|---|---|
| 1 | [F-2 Return a book](plan/M-1-members-borrow-books/E-1-lending/F-2-return-a-book/README.md) | feature | [M-1 Members can borrow books](plan/M-1-members-borrow-books/README.md) › [E-1 Lending](plan/M-1-members-borrow-books/E-1-lending/README.md) | finishing — it is a draft | Asha |
<!-- /spry:backlog -->
