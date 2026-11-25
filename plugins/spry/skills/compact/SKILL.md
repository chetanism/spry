---
name: compact
description: Bring a file back under its line budget, losing no fact. Use when spry check reports one over budget or AGENTS.md has grown long.
argument-hint: "[file, optional — default: every file spry check reports over budget]"
---

# spry — compact

- **Procedure:** `spry/process/compacting.md`. Read `chat.md` and `writing.md` beside it.
- **Scope:** `$ARGUMENTS`, or every file `python3 spry/tool/spry.py check` reports over budget.
- **Move, don't edit.** A rule you doubt stays where it is and goes in the report.
- **Show the moves** — one line per section and its destination — and apply only on a yes.
