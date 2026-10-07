---
title: Recording knowledge
summary: Where a decision, a convention or an external service's behaviour goes, and how it is written so the next session finds it.
audience: 7
---
# Recording knowledge

Run by `record`. Tone: audience 7. One thing per run; ask which kind if it is not obvious.

| Kind | When | Create |
|---|---|---|
| decision | a choice was made between options, and someone will later ask why | `spry.py new decision --title "<the decision, as a statement>"` |
| convention | a rule about how code is written here that the code does not make obvious | `spry.py new convention --title "<area>"`, or a new bullet in the area's existing file |
| external | a fact about how a service we depend on behaves | `spry.py new external --dependency "<service>" --title "<behaviour, as a statement>"` |
| knowledge rule | a security, performance or constraint rule | a numbered rule in `security.md` / `performance.md` / `constraints.md` |

## Write it

- Fill every section of its template; `summary` is the one line the index shows — make it say the fact.
- **Decision:** the options not taken and why. Superseding one → a new decision; the old one's
  `state` becomes `superseded by D-<n>`.
- **Convention:** one rule per bullet, each with its why after a dash. Over the budget → split the area.
- **External:** `source` is `observed` or `documented`; observed wins when they disagree — say so.
  Link the evidence.
- **Search first** (`spry.py related` on a draft, or `grep -ri` in `spry/knowledge/`): extend an
  existing entry rather than adding a second one about the same thing.

## AGENTS.md

Offer a line in `AGENTS.md` → `Must not` only when an agent will break the rule by default and no
tool can check it — the admission test at the top of that file. Never past its line budget: offer
what to move out instead.

## Finish

`spry.py check`; commit `docs(knowledge): <title>`. The `INDEX.md` line appears when CI regenerates
the indexes on the main branch.
