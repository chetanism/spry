---
title: Security
summary: Who may see what, and how personal data is handled.
audience: 6
---
# Security

## Rules

- **SEC-1** Only librarians can see a member's loans; a member will see only their own (M-2).
- **SEC-2** A library card number never appears in a log, error message or analytics event.
- **SEC-3** A desk session ends after 15 minutes without activity.

## Why

- Riverside's members' reading history is personal; the library committee asked for SEC-1 and SEC-2 (2026-09-25).
- The desk computer is in a public room (SEC-3).

## How it is checked

- SEC-1 — tests on every endpoint that returns loans.
- SEC-2 — a lint rule refuses logging any field named `cardNumber`.
- SEC-3 — manual, once per milestone.
