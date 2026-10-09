---
id: F-1
title: Lend at the desk
state: ready
owner: Asha
audience: 3
blocked_by: []
related: [F-2]
---
# F-1 · Lend at the desk

## Summary

- A librarian lends a book to a member by scanning the member's library card and the book.

## Who uses it

- **Librarian** — at the desk.

## How it works

1. The librarian scans the member's library card → the desk shows the member's name and current loans.
2. The librarian scans the book → the desk shows the title.
3. The librarian presses **Lend** → the desk confirms and prints a receipt with the due date.

## Rules

- **R-1** A member may have at most 3 books on loan at once.
- **R-2** A loan lasts 14 days; the due date is printed on the receipt.
- **R-3** A book can be on loan to only one member at a time.
- **R-4** A member with an overdue book cannot borrow another until it is returned.

## Where it appears

- The desk screen.
- The printed receipt.

## Out of scope

- Lending without a library card.
- Changing the due date by hand.

## Conflict check

- Checked 2026-09-30 against: E-1, F-2, glossary, security, performance, D-1
- Term: draft said "check out" → "lend", per the glossary
- Contradiction: Asha's notes allowed overdue members to borrow; the desk's paper rule does not → R-4 added (Asha, 2026-09-30)

## Stories

<!-- spry:children -->
| Story | State | Progress |
|---|---|---|
| [S-1 Lend a book](S-1-lend-a-book/README.md) | ready | not proven · 1 of 1 slices · 2 of 3 criteria proven |
| [S-2 Loan limit](S-2-loan-limit/README.md) | ready | in progress · 0 of 1 slices · 0 of 2 criteria proven |

| Bug | Severity | State | Progress |
|---|---|---|---|
| [B-1 Due date a day early on evening receipts](bugs/B-1-due-date-a-day-early/README.md) | major | ready | 0 of 1 slices done |
<!-- /spry:children -->
