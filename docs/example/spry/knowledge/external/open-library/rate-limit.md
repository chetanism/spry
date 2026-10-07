---
title: Open Library — lookups are rate-limited without a User-Agent
summary: about 100 lookups per 5 minutes, then HTTP 429
dependency: Open Library
source: observed
confidence: medium
observed: 2026-10-03
affects: [F-1, SL-1]
audience: 7
---
# Open Library — lookups are rate-limited without a User-Agent

## Behaviour

- `GET https://openlibrary.org/isbn/<isbn>.json` without a `User-Agent` header: HTTP 429 after about 100 requests in 5 minutes.
- With a `User-Agent` naming the app and a contact email: no 429 seen in 1,000 requests.
- The documentation asks for a `User-Agent` but states no limit.

## Evidence

- Seeding 400 books on 2026-10-03: 429 from request 103 onward (`logs/seed-2026-10-03.txt`, not committed).

## What we do about it

- `src/books/openLibrary.ts` sends `User-Agent: Shelf/0.1 (ops@shelf.example)`.
- A book's details are stored on first lookup and never fetched again.
