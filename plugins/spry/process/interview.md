---
title: Interviewing
summary: How every spry interview is run — few questions at a time, defaults offered, answers written down at once.
audience: 7
---
# Interviewing

Used by `init`, `adopt`, `milestone`, `epic`, `feature` and `story`. Replies follow `chat.md`;
tone follows the audience of the document being written.

## Protocol

- **At most 3 asks per reply.** Numbered, options lettered, one `(recommended)` — `chat.md`.
- **Offer, don't ask open questions.** Draft an answer from what is already known (the parent, the
  knowledge files, earlier answers, the code) and ask the person to confirm or correct it. An open
  question only when there is nothing to draft from.
- **Coarse to fine.** Settle the outline of a section before its details; never ask about a detail
  of something not yet agreed.
- **One section at a time,** in the template's order. Say which section you are on.
- **Plain words below audience 5.** No IDs without titles, no technical terms; translate any the
  person uses into the glossary's term and say so once.

## Writing it down

- **The document is the record.** Create it first (`spry.py new …`, state `draft`) and write each
  answer into it as soon as it is given — never hold answers in the conversation. Any agent, in any
  later session, resumes by reading the draft.
- **An answer not given is recorded, not invented.** Write it under `## Open questions` with who
  answers and by when, and move on.
- **A new word** the person uses for a new concept → a glossary row in the same change; a second word
  for an existing concept → use the glossary's, add theirs to `Don't say`.

## Stop rule

Stop asking when every required section of the template has content a reader could act on. Do not
fill optional sections for the sake of it — delete them.

## Calibrating depth

| The person says | Do |
|---|---|
| "you decide" / "whatever's standard" | take your `(recommended)` option, record it as an assumption under Open questions |
| detailed answers, more than asked | write them down; skip the asks they already answered |
| "I don't know yet" | record under Open questions; continue |
| drifts into a lower level (stories while defining a feature) | note it under `## Later` in your reply, not in the document; offer the next skill at the end |

## Finishing

1. Remove every guide comment and placeholder; delete empty optional sections.
2. Run the conflict check — `conflicts.md`.
3. **The review, before `ready`.** A plan item gets `/spry:review <ID>` — a new agent reads the
   draft as it stands in the working tree (`reviewing.md` §1–§4). Solo, it is the only second pair of
   eyes. Show its findings; on the person's yes, apply the accepted ones to the draft. Several items
   finished in one run are reviewed together, one agent each, in parallel.
   - `planning.review: "offer"` → offer it in one line instead, and go on at a no.
   - **A bug with replayable evidence** (`planning.md` → *Bugs and tasks*) skips it, and says so in
     one line.
4. Show the person a short summary at their tone; ask to mark it `ready`.
5. On yes: set `state: ready`; run `python3 spry/tool/spry.py check`; fix what it reports.
6. Commit (`docs(plan): <ID> <title>`) — the review's fixes are part of it. With a team configured
   and the path under a `review` rule, open a pull request for the reviewers instead of committing
   to the main branch; the agent's review came first, so they read a draft already checked.
