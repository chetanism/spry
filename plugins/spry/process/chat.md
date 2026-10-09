---
title: Chat rules
summary: The shape of every agent reply in a spry project — tags, asks, and tone by audience.
audience: 7
---
# Chat rules

Applies to every reply, from every agent, in every skill. **Tone** (vocabulary) comes from the
audience level; **shape** comes from this file and is the same at every level.

## Audience

- Use, in order: the personal override in `.spry/tone`, then the `audience` of the document the
  current skill is working on, then 5.
- **1–3** — plain words; no paths, code, commands or internals; an ID always with its title
  ("S-2 Loan limit").
- **4–6** — names screens, fields and data; no internals.
- **7–10** — paths as `path:line`, types, commands; IDs alone are fine.

## Shape

- Bullets, not prose. No preamble, recap, closing summary or restated question.
- Group under only the headings the reply needs, in this order:
  - `BLOCKED` — what stops progress, and on whom.
  - `DONE` — what the agent did.
  - `NEXT` — what the user should do next.
  - `FYI` — facts worth knowing; nothing to do.
  - `ASK` — questions for the user. Last, so the reader has the findings before the choice, and the
    question is where the reply ends.
- One fact per bullet. Add a reason only when leaving it out would mislead.
- Never quote back a diff or a file just written. Rationale only when asked.

## Tags

Every bullet starts with one tag in brackets.

| For | Tense | Tags |
|---|---|---|
| What the agent did | past | `[Added]` `[Changed]` `[Removed]` `[Fixed]` `[Moved]` `[Ran]` `[Checked]` `[Found]` `[Opened]` `[Closed]` |
| What the user should do | to-do verb | `[Review]` `[Decide]` `[Answer]` `[Approve]` `[Run]` `[Merge]` `[Test]` `[Fill]` |
| A fact | — | `[Note]` |

## Asks

- Number every ask from 1 in each reply, even when there is only one.
- Letter every option `a`, `b`, `c`, restarting per ask.
- The stem carries its own context — what is being chosen, and the fact it turns on, quoted
  inline. The reader answers without opening anything: "2b" is a full answer.
- One line per option, saying why it is or is not the better choice.
- Exactly one option marked `(recommended)` — except where config leaves the choice to the person
  without one (`slices.pick: ask`).

## Example — audience 2

```
DONE
- [Added] Story S-2 Loan limit, with 3 acceptance criteria
- [Found] S-2 overlaps S-1 Lend a book: S-1 now covers only the allowed case
NEXT
- [Review] S-2 Loan limit — the three "Done when" lines are what QA will test
ASK
1. Should a member with an overdue book be allowed to borrow another?
   a. No — they return the overdue book first (recommended): matches the desk's paper rule today
   b. Yes, up to the limit — simpler for members, but overdue books pile up
```

## Example — audience 8

```
DONE
- [Opened] SL-2 on `sl-2-refuse-over-limit`, draft PR #14
- [Found] Collision: SL-3 also edits `src/loans/service.ts` — SL-2 goes first, SL-3 rebases
NEXT
- [Review] SL-2 plan — `spry/plan/…/SL-2-refuse-over-limit.md`
- [Approve] start of coding
```
