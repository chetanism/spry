---
title: Checks for S-1 · Lend a book
audience: 4
---
# Checks · S-1 · Lend a book

## Scenarios

### AC-1 · Lend to a member under the limit

1. Open the desk and sign in as a librarian → the scan box is ready.
2. Scan library card `1001` → "Kiran" appears, with "0 books on loan".
3. Scan book `9780141439518` → "Pride and Prejudice" appears, **Lend** is enabled.
4. Press **Lend** → "Lent to Kiran"; Kiran now shows "1 book on loan".

### AC-2 · Receipt shows the due date

1. Do AC-1 steps 1–4 → the receipt prints.
2. Read the receipt → title "Pride and Prejudice", member "Kiran", due date 14 days from today.

### AC-3 · Book already on loan

1. Do AC-1 steps 1–4.
2. Scan library card `1002`, then book `9780141439518` → "Already on loan to Kiran"; **Lend** is greyed out.

## Check log

| Date | AC | Build | By | Result | Notes |
|---|---|---|---|---|---|
| 2026-10-04 | AC-1 | `a1c9e02` | Meera | pass | |
| 2026-10-04 | AC-2 | `a1c9e02` | Meera | pass | printed at 11:20 |
| 2026-10-04 | AC-3 | `a1c9e02` | Meera | pass | |
| 2026-10-06 | AC-2 | `a1c9e02` | Meera | fail | printed at 19:05, due date one day early → B-1 |
