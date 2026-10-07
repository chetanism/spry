---
id: D-1
title: Store the due date on the loan
summary: the due date is saved when a book is lent, never worked out again later
state: accepted
date: 2026-10-02
decided_by: [Ravi, Asha]
affects: [F-1, S-1, S-2]
audience: 7
---
# D-1 · Store the due date on the loan

## Context

- F-1/R-2 sets a loan at 14 days; Asha expects the length to change (holiday periods).
- If the due date is worked out from the loan date, changing the rule would move every existing due date.

## Decision

- `loans.due_on` is set once, when the book is lent, and never recalculated.

## Rejected

- Compute `lent_on + loan_days` on read — changes past loans when the rule changes.
- Store the loan length on each loan — same result with more arithmetic in every query.

## Consequences

- Changing the loan length affects only new loans.
- Overdue means `due_on < today`, nothing else (S-2).
