---
id: S-1
title: Lend a book
state: ready
owner: Asha
audience: 3
blocked_by: []
related: [S-2]
---
# S-1 · Lend a book

## Story

- **As** a librarian
- **I want** to lend a book to a member at the desk
- **So that** the member can take it home and we always know who has it

## Acceptance criteria

| AC | Given | When | Then |
|---|---|---|---|
| AC-1 | a member with fewer than 3 books on loan and no overdue book | the librarian scans their library card and a book, and presses **Lend** | the desk shows "Lent to" and the member's name, and the book shows as on loan to them |
| AC-2 | a book has just been lent | the receipt prints | it shows the title, the member's name and a due date 14 days from today (F-1/R-2) |
| AC-3 | a book already on loan | the librarian scans it | the desk shows "Already on loan to" and the member's name, and **Lend** cannot be pressed (F-1/R-3) |

## Not in this story

- Refusing a member who is at the limit or has an overdue book — [S-2 Loan limit](../S-2-loan-limit/README.md).

## Notes

- Test data: library card `1001` (Kiran, no loans), book `9780141439518` (Pride and Prejudice).

## Conflict check

- Checked 2026-10-01 against: F-1, S-2, glossary, security, D-1
- Overlap: S-2 Loan limit also described the "fewer than 3" case → S-1 covers lending that is allowed; S-2 covers refusals

## Slices

<!-- spry:children -->
| Slice | State | Covers |
|---|---|---|
| [SL-1 Record a loan](SL-1-record-a-loan.md) | done · PR #9 | AC-1, AC-2, AC-3 |
<!-- /spry:children -->

## Proof

<!-- spry:proof -->
| AC | Proven by |
|---|---|
| AC-1 | test `src/loans/lend.test.ts` — "S-1/AC-1 lends a book to a member under the limit" · test `src/loans/lend.test.ts` — "S-1/AC-1 refuses an unknown library card" · manual check 2026-10-04 · Meera · pass ([checks](checks.md)) |
| AC-2 | test `src/loans/lend.test.ts` — "S-1/AC-2 sets the due date 14 days after the loan" · manual check 2026-10-06 · Meera · fail ([checks](checks.md)) |
| AC-3 | test `src/loans/lend.test.ts` — "S-1/AC-3 refuses a book already on loan" · manual check 2026-10-04 · Meera · pass ([checks](checks.md)) |

Open bug: [B-1 Due date a day early on evening receipts](../bugs/B-1-due-date-a-day-early/README.md) breaks AC-2.
<!-- /spry:proof -->
