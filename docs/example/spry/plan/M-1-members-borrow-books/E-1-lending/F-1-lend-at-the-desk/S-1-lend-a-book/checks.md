---
title: Checks for S-1 · Lend a book
audience: 4
---
# Checks · S-1 · Lend a book

## Scenarios

### Before you start

| What is needed | Who provides it |
|---|---|
| The desk, with its card scanner and receipt printer | Whoever prepares the environment |
| A librarian account for the desk | Whoever prepares the environment |
| The test data in the story's Notes: four members with no loans and nothing overdue, and three books not on loan | Whoever prepares the environment, from the seed |

**Not through the screen:** members and books. Nothing in the product adds them yet; they come
from the seed. Each scenario uses members and a book no other scenario touches, so they run in any
order — once each per seed. AC-2 runs after 18:30.

### AC-1 · Lend to a member under the limit

**Type** happy path · **Where** the desk · **Ready** yes

1. Sign in at the desk as the librarian → the desk asks for a library card.
2. Scan Kiran's card, `1001` → "Kiran" appears, with "0 books on loan".
3. Lend Kiran *Pride and Prejudice* (`9780141439518`) → "Lent to Kiran"; Kiran now shows "1 book on
   loan".
4. Scan the same book again → "Already on loan to Kiran".

### AC-2 · Receipt shows the due date

**Type** happy path · **Where** the desk · **Ready** yes

1. After 18:30, signed in at the desk as the librarian, lend Ana (card `1002`) *Emma*
   (`9780141439587`) → the receipt prints. Evening receipts are the ones B-1 got wrong.
2. Read the receipt → title "Emma", member "Ana", and a due date exactly 14 days from today — not
   13, not 15.

### AC-3 · Book already on loan

**Type** negative · **Where** the desk · **Ready** yes

1. Signed in at the desk as the librarian, lend Ravi (card `1005`) *Persuasion* (`9780141439686`)
   → "Lent to Ravi".
2. Scan Mei's card, `1006`, and try to lend Mei *Persuasion* → "Already on loan to Ravi", and the
   book cannot be lent.
3. Scan Mei's card again → still "0 books on loan"; scanning *Persuasion* still shows it on loan to
   Ravi.

## Check log

| Date | AC | Build | By | Result | Notes |
|---|---|---|---|---|---|
| 2026-10-04 | AC-1 | `a1c9e02` | Meera | pass | |
| 2026-10-04 | AC-2 | `a1c9e02` | Meera | pass | printed at 11:20 |
| 2026-10-04 | AC-3 | `a1c9e02` | Meera | pass | |
| 2026-10-06 | AC-2 | `a1c9e02` | Meera | fail | printed at 19:05, due date one day early → B-1 |
