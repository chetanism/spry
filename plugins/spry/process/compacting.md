---
title: Compacting
summary: How a file past its line budget is brought back under it by moving whole sections to the files that own them — losing no fact, leaving a pointer behind.
audience: 7
---
# Compacting

Run by `compact`. Tone: audience 7. Files grow from slices, records and interviews; nothing else
takes lines out. **This moves text; it does not edit it.** Deciding a rule is wrong or has lapsed
is not part of a compaction — a line whose truth you doubt goes in the report, unchanged.

## 1. Measure

1. `python3 spry/tool/spry.py check` lists every file over its budget (`budgets` in config).
   `AGENTS.md` first: it is read on every task, so every line costs on every task.
2. A file named by the person but under budget: say so with its count and stop. A compaction with
   nothing to compact is how a file loses something somebody needed.
3. Record each file's starting count.

## 2. What stays

**`AGENTS.md`** keeps a line only if it passes the admission test at its top: a **pointer**, a
**rule an agent breaks by default**, or a **rule no tool can check**. Ask of each line: *would an
agent write the wrong code without it, on a task that never opens the file it came from?*

Never leaves, whatever it weighs: the admission test, *Project*, *Must not*, *Where things are*.
If those alone are over budget, the finding is that the budget is too small — propose a number
(a `/spry:process-change`) rather than gutting them.

**A knowledge file** over budget becomes `INDEX.md` + one file per item (`writing.md` → *Size*),
each item with a `title` and `summary` the index is generated from.

**A plan document** over budget is usually doing two jobs — a feature holding its stories' detail,
a slice holding a design. Move the detail to where it belongs, or split the item; a split of a
`ready` item goes through its planning skill, not here.

## 3. Where it goes

| What it is | Goes to |
|---|---|
| Why one option was chosen | a decision (`/spry:record`), and the line points at its `D-n` |
| How code is written here — a pattern, its example, its exception | `knowledge/conventions/<area>.md`; one line stays if agents break it by default |
| How a service really behaves | `knowledge/external/<service>/` |
| A security or performance rule | `knowledge/security.md` · `performance.md` |
| A procedure with steps | the process file or skill that runs it (`/spry:process-change`) |
| What a feature or story requires | the plan item that owns it |
| What we used to do and stopped | delete it — git keeps it, and a stale rule here reads as live |

A section with no destination in this table stays where it is and goes in the report.

## 4. Rules of the move

- **No fact is lost.** Each removed sentence is in its destination — word for word or shortened —
  or deleted as superseded and named in the report.
- **Leave a pointer** where a section was: one line, what the rule is and where it now lives. A
  section that just vanishes reads as a rule that was dropped.
- **Never restate.** Once a rule lives elsewhere, link it. Two wordings are two rules.
- **Never move into another always-loaded file.**
- **The destination keeps its shape:** its template's sections, its budget, its front-matter.
- **One commit per destination**, so a reviewer reads one move at a time.

## 5. Verify and deliver

1. `python3 spry/tool/spry.py check` — clean, every budget held.
2. **Read `AGENTS.md` end to end as if new to the project.** It must still answer: what this is,
   where things live, how work is done, what must never be done.
3. **Diff facts, not lines:** for each removed section, name the file and heading that now holds
   it. One you cannot point at goes back.
4. On a branch; commit `docs: compact <file>`; through a pull request when a team is configured.
   The PR body: a table of moves — what left, where it lives now, the line left behind — and the
   counts before and after against the budget.
5. **Report what was not moved:** sections with no honest destination, lines whose truth you
   doubted. Those are the person's to decide.
