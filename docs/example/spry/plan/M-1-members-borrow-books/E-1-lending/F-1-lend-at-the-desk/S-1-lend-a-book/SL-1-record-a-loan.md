---
id: SL-1
title: Record a loan
state: closed
owner: Ravi
audience: 8
covers: [AC-1, AC-2, AC-3]
branch: sl-1-record-a-loan
pr: 9
blocked_by: [T-1]
related: []
---
# SL-1 · Record a loan

## Work order

### Summary

- A librarian can lend a book from the desk: scan card, scan book, press **Lend**.
- The loan is saved with its due date, a receipt prints, and a book already on loan is refused.

### Covers

- [S-1](README.md) AC-1, AC-2, AC-3

### Plan

- `db/migrations/0003_loans.sql` — `loans` table; `due_on date not null`; partial unique index on `book_id where returned_at is null` (F-1/R-3)
- `src/loans/lend.ts` — `lend(memberId, bookId, today): Result<Loan, LendError>`
- `src/loans/lend.test.ts` — unit tests below
- `src/desk/LendPanel.tsx` — scan flow and **Lend** button
- `src/desk/receipt.ts` — receipt text with due date

### Must not

- [D-1](../../../../../knowledge/decisions/D-1-store-the-due-date.md) — store `due_on`; never derive it later from `lent_on`.
- [SEC-2](../../../../../knowledge/security.md) — the card number never reaches a log line; log `memberId`.

### Tests

- "S-1/AC-1 lends a book to a member under the limit"
- "S-1/AC-2 sets the due date 14 days after the loan"
- "S-1/AC-3 refuses a book already on loan"

### Demo

```bash
pnpm db:reset && pnpm db:seed && pnpm dev
open http://localhost:3000/desk   # card 1001, book 9780141439518, press Lend
```

### Conflict check

- Checked 2026-10-02 against: S-1, S-2, D-1, security, performance, open slices (none)
- Dependency: needs CI to run the tests → `blocked_by: [T-1]`

## Close summary

### What changed

- `src/desk/receipt.ts` formats the date with the server's timezone; receipt printing tested by hand only (AC-2 manual).

### Falsify

| Control | Mutation | Expect | Result |
|---|---|---|---|
| book already on loan → `AlreadyOnLoan` | delete the check | S-1/AC-3 | caught |
| `due_on = today + 14` | `+ 13` | S-1/AC-2 | caught |
| unknown library card → `NoSuchMember` | delete the check | S-1/AC-1 | survived → added "S-1/AC-1 refuses an unknown library card"; caught |

### Follow-ups

- [D-1](../../../../../knowledge/decisions/D-1-store-the-due-date.md) recorded.
