---
title: Reviewing
summary: How a pull request — a slice, a plan document or anything else — or a plan item with no pull request is reviewed by fresh eyes, and how each finding reaches its author on the line it belongs to.
audience: 8
---
# Reviewing

Run by `review`. Tone of this file: 8. Tone of what is posted: §6.

**The reviewer is a mate, not a tool.** Every review is done by fresh eyes: an agent that did not
write what it reads and carries nothing from the session that did. Solo, it is the second pair of
eyes there is no teammate for. On a team, it reads before a teammate does, or for them.

**It reads and comments.** The reviewing agent never checks a branch out, edits one, pushes,
approves unless told to, or merges. The one change it makes is a solo plan item's accepted fixes
(§5). Fixing what it found, and merging, is the session that ran the review — and only on the
person's answer (§5a).

## 1. What is reviewed

The argument is a PR number, `SL-n`, or a plan item ID (`S-3`, `F-2`, `B-1` …); several are reviewed
together. With no argument, the current branch's PR.

| Kind | Known by | Checks |
|---|---|---|
| Slice | branch `sl-<n>-*`, or `SL-n` | §3a |
| Plan | every changed file is under `spry/`, and no slice file is among them | §3b |
| Other | anything else | §3c |

- A plan item with no open PR — solo, the plan is committed straight to the main branch — is read as
  it stands there.
- **The PR:** `gh pr view <n> --json number,headRefName,headRefOid,author,files,body`, and
  `gh pr diff <n>`.
- **Its files:** `git fetch origin <branch>`, then `git show origin/<branch>:<path>`. **Never check
  the branch out**: the session may be mid-slice or in a worktree, and a review must leave nothing
  behind.
- Skip what is generated: `INDEX.md` files, `spry/BACKLOG.md`, `spry/COVERAGE.md`, and marker
  blocks.

## 2. Fresh eyes

- **A new agent does the review.** It is never the session that wrote the work, and never a fork of
  it. In Claude Code, that is the Agent tool with a new general-purpose agent, one per target, run
  in parallel.
- **Its prompt holds only:**
  - the target and its kind;
  - this file;
  - the output shape in §4.
- **Leave out why the work was written as it was.** That reasoning is what the review is testing.
- **An agent with no subagents:** ask the person to run `/spry:review <target>` in a new session.
- **Another review after fixes** gets another new agent. It writes its own findings before it reads
  the earlier ones. Then it says which of the earlier ones still stand.

## 3. Checks

### a. Slice

The question is not "is this good code". It is "is this what the work order said, and nothing it
said not to do".

1. **Read *For the reviewer* first.** It is at the top of the PR body and holds:
   - the criteria in words, and any that changed;
   - what falsify could not show;
   - what QA checks by hand.

   Then read the work order, then the diff.
2. **Plan.** Every file the plan named changed as it described. Any other file that changed is
   explained in `What changed`.
3. **Must not.** Each linked rule still holds in the diff.
4. **Tests.**
   - At least one per covered criterion.
   - Each name cites `<story>/AC-<n>`.
   - Each asserts what the criterion's *Then* says, not something nearby.
5. **Falsify.** Every row reads `caught`. A `survived` or `skipped` row needs a reason you accept.
6. **Conventions.** The areas the diff touches (`spry/knowledge/conventions/INDEX.md`).
7. **Demo.** Run it when it can run locally. If you did not run it, say so.

### b. Plan

For a milestone, epic, feature, story, bug, task or `checks.md`.

**Read first:**

- the item, its parent and the parent's parents;
- its siblings (`spry.py related <file>`); open siblings are read on their branches;
- `spry/knowledge/glossary.md`, the knowledge files in `always_check`, and the decisions whose
  `affects` names it or a parent;
- `planning.md` §4 and `writing.md`.

**The rule everything serves:** the parent is elaborated, never extended.

1. **Fidelity.**
   - Anything the item adds that its parent does not ask for is an extension.
   - Anything it contradicts is a conflict.
2. **What binds it.** Decisions, conventions, external behaviour, and the rules of its feature.
3. **The code, where it is already built.** An adopted project describes behaviour that exists.
   - Find the routes, screens, commands and domain code.
   - Check every sentence a tester will act on against what the product does.
   - A disagreement the item does not name is a finding.
4. **A tester will trip.**
   - A criterion breaks `planning.md` §4: not observable at audience 3, two behaviours in one, or a
     *Then* that cannot fail.
   - A precondition QA cannot set up.
   - A step the story skips.
   - A word that differs from the one on screen.
   - Two lines that contradict each other.
5. **Words.**
   - A term used but missing from the glossary, or listed in its *Don't say* column.
   - A term used differently in a sibling.
6. **Who decided.** An open question the drafter answered, or a criterion changed without its
   owner. Only the owner can make either call.
7. **Conflict check.** It is present and honest: it names the candidates `related` lists.

### c. Other

1. **Claims.** The diff does what the title and body say, and nothing they do not mention.
2. **Tests.** Every behaviour that changed has a test.
3. **Conventions.** The areas the diff touches.
4. **Risk.** Look at inputs, permissions, secrets and data that is deleted or migrated.
5. **Kind of change.** A behaviour people see, changed with no slice behind it, has no criterion to
   prove it. Report it as a `Should`, and name the slice, bug or task it should have been.

## 4. Findings

- **Each finding has:**
  - `path:line`, or a range;
  - a severity: `Blocker`, `Should` or `Nit`;
  - what is wrong, and why;
  - the replacement text, wherever the fix is wording.
- **Verify every finding before the person sees it.**
  - Open the line the finding rests on — code, plan or knowledge — and read it.
  - An agent's claim is a lead, not evidence. Drop any finding you cannot point at.
  - Example: a review once reported that the browser blocks a blank email. The input had no
    `required`, so the browser did not block it. One look would have caught that.
- **Report in `chat.md`'s shape:**
  - one `[Found]` bullet per blocker and per `Should`;
  - the `Nit`s as a count, not a list.
- **Name what the merge will ask about**, from *For the reviewer*: falsify rows not `caught`, with
  their reasons, and criteria QA checks by hand. One answer can then cover them.
- **Ask 1** is what happens next — one choice, so one answer carries the review through:
  - a. Post, fix every Blocker and Should as found, then merge (§5a);
  - b. Post, and fix — stop before the merge;
  - c. Post only;
  - d. Neither.

  Offer *a* and *b* only where this session may change the branch: a slice or plan PR that is your
  own. Recommend *a* when every fix is the finding's own suggestion or as local; *c* when a fix is a
  choice for the author or the owner. On a solo plan item with no PR, Ask 1 is whether to apply the
  fixes — all, the ones named, or none.
- **Then one ask per open question the item puts to its owner.** Each one gives the context, the
  options, and a recommendation naming what was read. The answers become comments too (§5).

## 5. Post — only on a yes

**With a PR**, post one review.

- **Event:**
  - `REQUEST_CHANGES` when there is a blocker, otherwise `COMMENT`.
  - `APPROVE` only when the person says to approve.
  - **On your own PR, only `COMMENT`.** It is your own when
    `gh pr view <n> --json author -q .author.login` equals `gh api user -q .login`. GitHub refuses
    the other events there, and solo, every PR is your own.
- **Body:** one line.
- **Comments:** one inline comment per finding.
- **Build it, check it, post it:**

  ```bash
  mkdir -p .spry/review && gh pr diff <n> > .spry/review/<n>.diff
  # .spry/review/<n>.json: {commit_id: <headRefOid>, event, body, comments: [
  #   {path, line, side: "RIGHT", start_line?, start_side?: "RIGHT", body}]}
  python3 spry/tool/spry.py review-check .spry/review/<n>.json --diff .spry/review/<n>.diff [--own]
  gh api -X POST repos/{owner}/{repo}/pulls/<n>/reviews --input .spry/review/<n>.json
  ```

  Post only after `review-check` prints `ready to post`. It refuses:
  - a line outside the diff;
  - a suggestion that is not closed, or that changes nothing;
  - two suggestions that overlap;
  - an event GitHub refuses on your own PR.

**Rules for comments:**

- **Anchor each comment on exactly the lines its suggestion replaces**, from `start_line` to `line`.
  A posted comment cannot be moved. If the anchor is wrong, delete it
  (`gh api -X DELETE repos/{owner}/{repo}/pulls/comments/<id>`) and post it again.
- **Every comment that proposes wording carries one suggestion**, so the author can apply it in one
  click:

  ````
  ```suggestion
  the replacement lines, whole, exactly as they should read
  ```
  ````

  An empty block deletes the lines.
- **Two suggestions never overlap.** Fold one into the other, and say so in the second comment.
- **A fix that applies in several places** is posted once, on its first line, naming the others. A
  place whose wording differs gets its own comment and its own suggestion.
- **To add a line or a row**, suggest it on the line next to it: that line, plus the new one.
- **An owner's answer to an open question** goes on the question's lines. Its suggestion marks the
  question settled, with the owner's name and the date.
- **To edit a posted comment:** `PATCH .../pulls/comments/<id>`. A submitted review cannot be deleted;
  if it has to go, replace its body with a pointer.

**With no PR** (a solo plan item):

- Show each finding with its replacement text.
- On a yes — to all of them, or to the ones the person names — apply exactly those, on the main
  branch.
- Run `spry.py check`, then commit `docs(plan): <ID> review fixes`. Change nothing else.

## 5a. Fix, then merge — on answer *a* or *b*

The session that ran the review does this, not the reviewing agent.

1. **Get onto the branch.** Already on it → go on. Otherwise `git switch <branch>`, only with a clean
   working tree; uncommitted work here → stop and ask.
2. **Fix exactly what was accepted:** each Blocker and Should, as its finding and suggestion say. A
   fix that turns out to need more than the finding said — another file, a design choice — is not
   made: stop and ask about that one.
3. **Re-run only what the fixes could change**, as `slicing.md` *Close* does: `spry.py gate`; falsify
   again when code changed (`merge-check` blocks a control with no row); the slice's *What changed*
   and the PR body when the diff did.
4. **Commit** `fix(<SL-n>): review findings`, and push once.
5. **On *a*,** run `/spry:merge` — every step. The answer was its step 6 yes, for the `!` items the
   report named; anything else it finds, it asks.

## 6. How comments read

Comments go out under the reviewer's name, to the author. **Their tone is the reviewed document's
`audience`** (`chat.md`), not the reviewer's own. A story PR reads in plain words; a slice PR names
paths.

- **Say what is wrong.** If the product works differently from the document, say so plainly, and
  say what it does.
- **Say why** it is that way, in one line.
- **Recommend one way, in one line:** the product or the document — which is right, and why.
- **At audience 6 or below:** no paths, function names or internals. An ID may stay, with its title.
- **Keep it short, but complete.** Use short sentences, and bullets when there are several points.
  The reader must not need to know the code to follow it. No scene-setting, and no hedging.

| Instead of | Write |
|---|---|
| "AC-2 is not in the feature." | "The feature never asks for this. The product does it, though: a member with an overdue book is stopped at the desk. Recommendation: keep it, and add it to the feature first." |
| "Wrong — `required` on the input." | "The page doesn't stop a blank email. The field isn't marked required, so the form sends it and the server rejects it. The sentence just needs to say so." + a suggestion |

## 7. Close

- **With a PR:** report the review's link, the number of comments, and how many carry a suggestion.
- **With a team:** name in `NEXT` who else must read it — the roles `team.review` gives for its
  paths.
- **Solo plan item:** report the commit.
