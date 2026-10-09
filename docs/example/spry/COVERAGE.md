---
title: Coverage
summary: How much of the plan is defined, built and proven, and what is built but not yet proven.
audience: 3
---
# Coverage

How much of the plan is defined, built and proven. A criterion is proven when a test names it in
its title, or its latest manual check passed. CI on the main branch writes the block below with `spry index`;
on any branch, `python3 spry/tool/spry.py coverage` prints it.

<!-- spry:coverage -->
### Totals

| | Done | Defined | |
|---|--:|--:|--:|
| Milestones | 0 | 1 | 0% |
| Epics | 0 | 1 | 0% |
| Features | 0 | 2 | 0% |
| Stories | 0 | 2 | 0% |
| Acceptance criteria proven | 2 | 5 | 40% |
| Slices closed | 2 | 4 | 50% |
| Tasks | 1 | 1 | 100% |
| Bugs fixed | 0 | 1 | 0% |

### By milestone

| Milestone | State | Stories done | Criteria proven | Open bugs |
|---|---|--:|--:|--:|
| [M-1 Members can borrow books](plan/M-1-members-borrow-books/README.md) | ready | 0 of 2 | 2 of 5 | 1 |

### Built, not proven

Every slice is closed and these criteria still have no passing proof — no test names them in its title, and no manual check passed.

| Story | Not proven |
|---|---|
| [S-1 Lend a book](plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/S-1-lend-a-book/README.md) | AC-2 |

### Cited outside a test's name

Not proven, and cited only in a comment or in code. Moving the ID into the test's title string proves it.

_None._
<!-- /spry:coverage -->
