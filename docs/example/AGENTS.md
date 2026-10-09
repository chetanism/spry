# AGENTS.md

**Admission test.** A line stays here only if it is a **pointer** (where something lives), a **rule an
agent breaks by default**, or a **rule that cannot be checked by a tool**. Everything else goes to
`spry/knowledge/` and is linked from its `INDEX.md`.

## Project

- Shelf — lending desk and member accounts for small community libraries
- Stack: TypeScript, Node 24, Postgres 17, Vitest; pnpm workspace
- Plan and status: `spry/plan/` · `python3 spry/tool/spry.py status`
- Config: `spry/spry.config.json` — inside `spry/`, not at the repository root

## How work is done

- Follow `spry/process/` — chat (`chat.md`), writing (`writing.md`), conflict check (`conflicts.md`).
- Work arrives as a slice: `/spry:slice-open` before any code, `/spry:slice-close` before merge.
- Start from this file and the work order; open a process file only when a step names it, and
  search before planning or coding: `python3 spry/tool/spry.py find "<words>"`.
- Use the words in `spry/knowledge/glossary.md`; never their banned synonyms.

## Replies

- Bullets under `BLOCKED` · `DONE` · `NEXT` · `FYI` · `ASK`; no preamble or recap.
- `[Past-tense]` tags for what you did, `[To-do]` tags for what the user should do.
- Asks numbered, options lettered, one `(recommended)`.
- Tone from the audience of the document in hand, or `.spry/tone`.

## Commands

- Before close, and whenever tests are wanted: `python3 spry/tool/spry.py gate` — check, fast
  checks, affected tests; skipped while only documents changed
- Never run the full suite; CI does, and `/spry:test-all` when asked
- Check the process: `python3 spry/tool/spry.py check`

## Must not

- Never compute a due date from the loan date — read `loans.due_on` (D-1).
- Never log a library card number (SEC-2) — use the member ID.

## Where things are

- Conventions: `spry/knowledge/conventions/INDEX.md`
- Decisions: `spry/knowledge/decisions/INDEX.md`
- External services: `spry/knowledge/external/`
- Security · performance: `spry/knowledge/security.md` · `spry/knowledge/performance.md`
