---
id: B-1
title: Due date a day early on evening receipts
state: ready
owner: Meera
audience: 4
severity: major
breaks: [S-1/AC-2]
blocked_by: []
related: [SL-1]
---
# B-1 · Due date a day early on evening receipts

## What happens

- A receipt printed after about 18:30 shows a due date one day earlier than 14 days from today.

## What should happen

- The due date is always 14 days from the day of the loan (F-1/R-2, [S-1](../../S-1-lend-a-book/README.md) AC-2).

## Steps to reproduce

1. After 18:30, lend book `9780141439518` to library card `1001`.
2. Read the due date on the receipt → it is 13 days from today.

## Where

- Build `a1c9e02`, Riverside desk computer, Chrome.

## Impact

- Every loan made in the evening — about a quarter of all loans. Members may return books a day early or be told they are overdue when they are not.

## Slices

<!-- spry:children -->
| Slice | State |
|---|---|
| [SL-4 Due date in the library's time zone](SL-4-due-date-in-library-time-zone.md) | planned |
<!-- /spry:children -->
