---
id: SL-2
title: Refuse a loan over the limit
state: open
owner: Ravi
audience: 8
covers: [AC-1, AC-2]
branch: sl-2-refuse-over-limit
pr: 14
blocked_by: []
related: [SL-1]
---
# SL-2 · Refuse a loan over the limit

## Work order

### Summary

- The desk refuses a loan when the member already has 3 books, or has an overdue one.
- The refusal shows on the desk as soon as the library card is scanned, before any book.

### Covers

- [S-2](README.md) AC-1, AC-2

### Plan

- `src/loans/eligibility.ts` — `canBorrow(memberId, today): Result<void, AtLimit | Overdue>`; reads `loans.due_on` (D-1)
- `src/loans/lend.ts` — call `canBorrow` before inserting; same errors
- `src/desk/LendPanel.tsx` — show the refusal after the card scan; disable **Lend**
- `src/loans/eligibility.test.ts` — unit tests below
- `db/seed.ts` — members `1003` (3 loans) and `1004` (one overdue)

### Must not

- [D-1](../../../../../knowledge/decisions/D-1-store-the-due-date.md) — overdue means `due_on < today`, from the stored date.
- [PERF-1](../../../../../knowledge/performance.md) — card scan to screen under 1 s: one query for both checks.

### Tests

- "S-2/AC-1 refuses a member with 3 books on loan"
- "S-2/AC-2 refuses a member with an overdue book"

### Demo

```bash
pnpm db:reset && pnpm db:seed && pnpm dev
open http://localhost:3000/desk   # card 1003 → "Limit reached"; card 1004 → "Return overdue book first"
```

### Conflict check

- Checked 2026-10-07 against: S-2, S-1, SL-1, D-1, security, performance, open slices (none)
- Overlap: SL-1's `lend.ts` already returns `LendError` → `AtLimit` and `Overdue` added to that union, not a new type
- Dependency: B-1 changes how "today" is worked out → `today` is a parameter here, so B-1's fix applies to both
