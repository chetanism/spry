---
id: S-2
title: Loan limit
state: ready
owner: Asha
audience: 3
blocked_by: []
related: [S-1]
---
# S-2 · Loan limit

## Story

- **As** a librarian
- **I want** the desk to stop a loan the rules do not allow
- **So that** I never have to remember the rules or argue about them

## Acceptance criteria

| AC | Given | When | Then |
|---|---|---|---|
| AC-1 | a member with 3 books on loan | the librarian scans their library card | the desk shows "Limit reached: 3 books on loan" and **Lend** cannot be pressed (F-1/R-1) |
| AC-2 | a member with an overdue book | the librarian scans their library card | the desk shows "Return overdue book first:" and the overdue book's title, and **Lend** cannot be pressed (F-1/R-4) |

## Not in this story

- Lending that is allowed — [S-1 Lend a book](../S-1-lend-a-book/README.md).
- What the member sees after returning a book — [F-2 Return a book](../../F-2-return-a-book/README.md).

## Notes

- Test data: library card `1003` (Sam, 3 books on loan), library card `1004` (Lee, one book overdue since 2026-09-20).

## Conflict check

- Checked 2026-10-05 against: F-1, S-1, F-2, glossary, security
- Overlap: S-1 described the "fewer than 3" case → S-1 keeps allowed lending; S-2 has the refusals
- Contradiction: overdue members — allowed in the draft, refused by the paper rule → refused; F-1/R-4 (Asha, 2026-09-30)

## Slices

<!-- spry:children -->
| Slice | State | Covers |
|---|---|---|
| [SL-2 Refuse a loan over the limit](SL-2-refuse-over-limit.md) | open · PR #14 | AC-1, AC-2 |
<!-- /spry:children -->

## Proof

<!-- spry:proof -->
| AC | Proven by |
|---|---|
| AC-1 | not yet |
| AC-2 | not yet |
<!-- /spry:proof -->
