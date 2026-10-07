---
title: Test scenarios
summary: How a story's acceptance criteria become the steps QA follows by hand, and how a manual check is logged.
audience: 6
---
# Test scenarios

Run by `test-scenarios`. Tone: audience 4 — the reader is QA: screens, fields, messages, nothing internal.

## Write them

1. The story must be `ready`. Read it, its feature's rules, and its `Notes` (test data).
2. `python3 spry/tool/spry.py new checks --parent S-<n> --title x` creates `checks.md` from the
   template; an existing one is extended, never rewritten.
3. One `### AC-<n> · <short name>` per criterion that is not dropped, in order. `spry check` fails
   on a scenario for a criterion the story does not have.
4. Each scenario: numbered steps a tester follows by hand, each `<what to do> → <what you should
   see>`, with the exact data to use. Start from a state the tester can reach; never "assume".
5. Add a scenario for a boundary only when the criterion has one ("3 books" → also try 2 and 4).
6. Read them back with QA; adjust; commit `docs(qa): scenarios for S-<n>`.

## Log a check

- One row per criterion per run in `## Check log`, appended, never edited:
  `| date | AC-n | build | who | pass / fail | notes |`.
- `build` is what was tested: a version, a commit, a deploy.
- **The latest row for a criterion decides it.** A `fail` un-proves the criterion even where a test
  passes; record a bug (`/spry:bug`) and put its ID in the notes.
