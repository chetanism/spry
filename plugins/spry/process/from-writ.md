---
title: From writ
summary: Adopting a project that ran writ — the mapping file writ's agent writes first, and how adopt turns it into the plan.
audience: 7
---
# From writ

`/spry:adopt` for a project that ran writ. It works in two halves. Before adopt, writ's own agent
cleans up in writ's terms and writes a mapping file (§1). The person reviews it, and adopt then
builds spry from it (§2). Nothing is investigated twice. Read with `setup.md` *Adopt — what
changes*; where the two differ, this file wins.

## 0. Before anything is written

- **The writ folder** holds `BRD.md`, `ID-REGISTRY.md` and a `*SLICE-QUEUE.md`, usually `canon/`.
  Below, `<canon>`.
- **Stop unless `<canon>/to-spry.md` exists**, and its first line under the title reads
  `Status: approved <date> by <name>`. If it doesn't, `NEXT`: run the pre-work. writ's agent writes
  the file in the format in §1, and the person approves it.
- **Stop while work is in flight**: a queue row in progress, or an open pull request for a writ
  slice. A half-built writ slice has no home in spry, so finish it or park it first.
- **Work on a branch**, `spry-adopt`: one commit per step of §2, and one pull request at the end.

## 1. The mapping file — `<canon>/to-spry.md`

writ's agent writes this file, in writ's terms. It assigns no spry IDs: epics, features and stories
are titles, and adopt numbers them. Sections, in this order:

### 1. Tree

- Milestones, from writ's milestone register. Under each: epics, then features, then stories, as a
  nested list. Each line is a title plus one line of purpose.
- Plain words, written for a reader who isn't technical. Every link is 1:many.
- A story is one thing a person does. A requirement that is a whole job of its own is a story; most
  requirements become a criterion of one.

### 2. Identifiers

One table per **traceable** family in `ID-REGISTRY.md`. The registry declares families, not IDs;
the IDs come from each family's declaring section, exactly as writ's ledger reads them. Every
declared ID appears exactly once, so the row count equals the ledger's total.

| writ ID | Epic | Feature | Story | As | State | Note |
|---|---|---|---|---|---|---|

- **As** — what the ID becomes:
  - `ac`: a criterion of that story. This is the default for anything a test can show.
  - `story`: the ID is the whole story. Note says which of its sections become criteria.
  - `rule`: a rule of that feature (`F-n/R-n`), which its stories obey. Leave Story blank.
  - `knowledge:<path>`: a rule, decision or convention that many features obey, such as
    `knowledge:security.md`, `knowledge:decisions` or `knowledge:conventions/api.md`. Note says
    why no single story owns it.
  - Nothing proves a `rule` or `knowledge` row, so prefer `ac` on a platform story whenever a test
    can prove it.
  - `milestone`: an exit criterion of a milestone, such as a gate.
  - `drop`: superseded or out of scope. Note says why.
- **By kind of family**:
  - requirement → `ac` or `story`.
  - invariant → `ac` on a platform story where tests prove it; otherwise `knowledge:security.md` or
    `knowledge:conventions/…`.
  - decision (strategic or spec) → `knowledge:decisions`.
  - design principle or IA → `knowledge:conventions/…`.
  - milestone gate → `milestone`.
  - process rule → `drop`, because spry's process replaces it. If the rule is still wanted, list it
    in §5 as well.
- **State**: `done` only when writ's ledger shows the ID satisfied, meaning a test cites it. Every
  other ID is `open`. Partial coverage is `open`, with `partial: <what is missing>` in Note.
- Epic, Feature and Story are titles from §1. Leave them blank for `knowledge`, `milestone` and
  `drop` rows, and Story blank for `rule` rows.

### 3. Work not built

Queue rows that aren't done yet, whether planned or not started:

| writ slice | Story | Note |
|---|---|---|

The row itself doesn't move, because spry opens a slice when work on it starts. What it would have
built must show up in its story's criteria. Rows that will never be built were dropped in the
clean-up and don't appear here.

### 4. Documents

One row for each file under `<canon>` that isn't a requirement detail (§7), a decision record, a
slice record or a work order:

| path | keep → spry destination, or history | Note |
|---|---|---|

`history` means the file stays only in git history.

### 5. Local process changes

Every way the project's process differs from stock writ, made on purpose: rules in `CLAUDE.md`,
registers, scripts, checks, templates and skills.

| change | where | why it was added — what went wrong without it | still useful? |
|---|---|---|---|

### 6. Open questions

Numbered, each with a recommendation. Adopt starts only when every question has an answer.

### 7. Requirement details

Only when writ kept detail files: one file per requirement saying what a person would see, with
job stories, personas, boundary cases and scenarios (usually `<canon>/spec/requirements/`). Each
can be longer than a story may be, and usually holds several jobs, so writ's agent plans the split.

One row per `##` section of every detail file, in file order. A section whose parts go to different
places gets one row per part, saying which part in Note.

| detail file | section | goes to | Note |
|---|---|---|---|

- **section**: the heading as written, such as `Story 3 — a different standing at each place`.
- **goes to**, each naming a story by its §1 title:
  - `story: <story>` — the story's *As / I want / So that*. Usually the summary and the personas.
  - `ac: <story>` — criteria of that story. Each "Story n" of the file is a job: criteria on the
    requirement's story, or a story of its own under the same feature when it is a separate job,
    added to the tree in §1. Observable behaviour, and boundary and negative cases, are criteria
    too. A case that can't be reproduced by hand stays a criterion, proven by a test.
  - `checks: <story>` — scenarios in that story's `checks.md`: the steps of a job story,
    mandatory fields, preconditions and data. That file has no line budget, so the detail goes
    here.
  - `not-in-story: <story>` — *Not in this story*. Out of scope usually goes here.
  - `notes: <story>` — the story's Notes: words, examples, which screen or route.
  - `related: <story>` — `related:` and Notes. Decisions named in it become `D-n` with the rest.
  - `glossary` — terms the file defines.
  - `question` — an open question, copied to §6. Its answer lands where §6 says.
  - `history` — nothing to carry: reconciliation rows, an empty verification table, and the
    requirement's quoted text, which survives as the criteria. The original is kept anyway (§2
    step 3).
- A verification row that records a check by hand goes to `checks: <story>` as a check-log row,
  for the criterion it checked. Note gives that criterion.
- The requirement's own row in §2 is `story` or `ac`, as usual; its Note points to this table.

## 2. Adopt from the mapping

1. **Survey** as in `setup.md`, but skip what `to-spry.md` already says.
2. **Interview** topics a–c and e–j as usual, with drafts taken from the documents in §4: the BRD,
   personas, and the security and performance specs. Topic d has no questions: show the tree from
   §1 instead.
3. **Plan.** `spry.py new` top-down, in the tree's order, which is where the IDs come from.
   - Each `ac` row becomes one criterion row (Given / When / Then) in plain words. It keeps the
     requirement's meaning, but not its wording when that wording is technical.
   - A `story` row gets the criteria its Note names.
   - A story goes `ready` once every criterion is written. Its `## Conflict check` reads
     `Checked <date> against: <canon>/to-spry.md, approved <date>`.
   - **Requirement details** follow §7, row by row: criteria, `checks.md` scenarios, *Not in this
     story*, Notes, `related:` and glossary terms, each where its row says. writ IDs in the text
     become their spry IDs from the trail.
   - **Keep each detail file** by script, unchanged, at
     `spry/history/writ/requirements/<writ ID>.md`, under one first line:
     `> writ requirement detail, as written. writ IDs → [the trail](../../writ.md).`
     Every story built from it says so in Notes, with a link. `spry check` skips these files, and
     `spry find` lists them last.
4. **The trail**, `spry/history/writ.md`: one table from old to new, `| writ ID | now |`. `now` is
   one of `S-12/AC-3`, `F-2/R-1`, `D-41`, `knowledge/security.md SEC-4`, `M-2 exit` or `dropped`.
   It also maps writ milestones (`M0` → `M-1`), writ slices (to the story they built) and detail
   files (to the stories made from them). Add each row when its item is made, not afterwards.
5. **Built work.** Every story with at least one `done` row gets one slice, titled `Built under writ`:
   - `state: closed`, and `covers` lists the criteria from its `done` rows;
   - Summary links the writ slices that built it: `- Built under writ by [SL-WD2](<path>), …`;
   - Close summary reads: imported — built, reviewed and falsified under writ.
   The story counts as done once the step 6 renames make its tests cite it.

   **Keep the slice summaries.** By script, copy every writ slice summary (the `*.md` under
   `<canon>`'s slices folder, not its README, not `*.falsify.json`, not work orders) to
   `spry/history/writ/slices/<writ slice ID>.md`, adding `SL-` when the file name lacks it. Content
   unchanged, under one first line:
   `> writ slice summary, as written. writ IDs → [the trail](../../writ.md).`
   `spry check` skips these files; `spry find` lists them after current documents, marked
   `history`. Work orders stay in git history: the summary supersedes them.
6. **Tests.** Rewrite citations from the trail table, in test files only. Each writ ID that became a
   criterion becomes `S-n/AC-m`.
   - One ID maps to one criterion, so this is a mechanical replace. Do it with a script, run over
     the table, never file by file.
   - writ IDs that became knowledge, decisions or milestones stay as they are. They are harmless
     text.
   - Take care with prefixes the two share, such as writ's `D-3` and spry's `D-3`. Match only the
     families that became criteria.
   - **Only a test's name proves a criterion** — its title string or docstring, not a comment. writ
     counted comments too. The same script moves an ID cited only in a comment (`// FR-12`) into
     the title of the test right below it; where there is no such test, it lists the line. Every
     `done` row whose criterion is left unproven is named in the pull request.
   - Commit it on its own (`test: cite spry criteria instead of writ IDs`), then run the full suite.
     Only names changed, so the suite must stay green.
7. **Knowledge** follows the Documents table and the `knowledge:` rows. All decision records and
   decision-family IDs move to `knowledge/decisions/` as `D-n` in one ask (`setup.md`, adopt step
   4), and their old IDs go into the trail.
8. **Instructions.** `CLAUDE.md` → `AGENTS.md` under the admission test.
   - writ's process rules are dropped, because spry's process replaces them.
   - Every row in §5 gets a row in `knowledge/process-changes.md` with `Kind: from writ`. The spry
     repository sorts each one into: already in spry, port, project-specific, or drop.
9. **writ's machinery.** One ask to remove three things:
   - writ's skills. Those with a spry counterpart: `slice-open`, `slice-close`, `test-all`,
     `test-scenarios`, `security-audit`, `prelaunch`, `process-change`, `manual-test` (→ `explore`),
     `context-compact` (→ `compact`) and `requirement-review` (→ `review`). Those spry drops on purpose: `requirement-verify`,
     `coverage-review`, `change-request`, `cleanup` and `maintenance`. Any other skill is in §5
     and is decided there.
   - writ's CI workflows, if there are any (`ledger`, `size`).
   - The scripts that serve only writ: the ledger, velocity and falsify.
   Skills that belong to the project alone, such as `screen`, stay, and are listed in
   `process-changes.md`.
10. **Verify.**
    - `spry check` is clean.
    - Every row of §2 is in the trail.
    - By script: every `##` heading of every detail file has a row in §7, and every story, criterion
      and `checks.md` scenario that §7 names exists. Report the gaps; fix them before the pull
      request.
    - The done criteria, set beside the `done` rows, differ only where the pull request explains why
      — a comment-only citation is the usual reason.
11. **Retire `<canon>`** in the last commit. Ask first, after the person has compared `spry status`
    with writ's last ledger. The trail, the kept summaries and git history keep everything.

## Adopted before CH-7

A project that retired `<canon>` without keeping the slice summaries gets them back from git
history, on a branch, in one commit and one pull request:

1. `c=$(git log -1 --format=%H --diff-filter=D -- '<canon>/process/slices')^` — the last commit
   that still had them. Check that `git ls-tree -r --name-only "$c" '<canon>/process/slices'`
   lists them; if the folder had another name, use that.
2. By script, write each listed summary with `git show "$c:<path>"` to the place step 5 names,
   under the same first line.
3. By script, turn every `Built under writ by SL-…` line in the plan into links to those files.
   Report any writ slice with no file, and any file that no slice names.
4. `spry check` is clean, then open the pull request.
