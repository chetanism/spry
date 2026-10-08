---
name: adopt
description: Put spry around an existing codebase — survey the code first, then interview with the surveyed answers offered for confirmation, and write the plan, knowledge files, AGENTS.md and CI without blocking any existing code. Use once, on a project that already has code.
argument-hint: "[what the next piece of work is, optional]"
disable-model-invocation: true
---

# spry — adopt

Set up spry in a project that already has code. For a new project, use `/spry:init`.

- **Plugin root:** two folders above this file's folder (`…/plugins/spry`).
- **Procedure:** `<plugin root>/process/setup.md` — *Adopt — what changes* says the order. Read
  `interview.md`, `chat.md` and `writing.md` beside it first.
- **writ project?** A folder with `BRD.md`, `ID-REGISTRY.md` and a `*SLICE-QUEUE.md` (usually
  `canon/`) → also `<plugin root>/process/from-writ.md`, which wins where they differ.
- **Survey first, and say what you are doing** — one `DONE` bullet per area surveyed. Run commands
  that only read; ask before running the test suite (it may be slow or need services).
- **Already set up?** If `spry/README.md` exists, stop and offer `/spry:status`.
- **Resuming:** `spry/` without `spry/README.md` is a run that stopped part-way — setup.md §0 says how
  to continue. The survey is in `spry/knowledge/codebase.md`; don't repeat what it already holds.
- **Starting point:** `$ARGUMENTS`, if given, is the next piece of work — it seeds the roadmap.
