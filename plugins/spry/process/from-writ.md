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

One row for each file under `<canon>` that isn't a requirement detail, a decision record, a slice
record or a work order:

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
4. **The trail**, `spry/history/writ.md`: one table from old to new, `| writ ID | now |`. `now` is
   one of `S-12/AC-3`, `F-2/R-1`, `D-41`, `knowledge/security.md SEC-4`, `M-2 exit` or `dropped`.
   It also maps writ milestones (`M0` → `M-1`) and writ slices (to the story they built). Add each
   row when its item is made, not afterwards.
5. **Built work.** Every story with at least one `done` row gets one slice, titled `Built under writ`:
   - `state: closed`, and `covers` lists the criteria from its `done` rows;
   - Summary names the writ slices that built it;
   - Close summary reads: imported — built, reviewed and falsified under writ.
   The story counts as done once the step 6 renames make its tests cite it.
6. **Tests.** Rewrite citations from the trail table, in test files only. Each writ ID that became a
   criterion becomes `S-n/AC-m`.
   - One ID maps to one criterion, so this is a mechanical replace. Do it with a script, run over
     the table, never file by file.
   - writ IDs that became knowledge, decisions or milestones stay as they are. They are harmless
     text.
   - Take care with prefixes the two share, such as writ's `D-3` and spry's `D-3`. Match only the
     families that became criteria.
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
     `test-scenarios`, `security-audit`, `prelaunch`, `process-change`, `manual-test` (→ `explore`)
     and `context-compact` (→ `compact`). Those spry drops on purpose: `requirement-verify`,
     `coverage-review`, `change-request`, `cleanup` and `maintenance`. Any other skill is in §5
     and is decided there.
   - writ's CI workflows, if there are any (`ledger`, `size`).
   - The scripts that serve only writ: the ledger, velocity and falsify.
   Skills that belong to the project alone, such as `screen`, stay, and are listed in
   `process-changes.md`.
10. **Verify.**
    - `spry check` is clean.
    - Every row of §2 is in the trail.
    - The done criteria, set beside the `done` rows, differ only where the pull request explains why.
11. **Retire `<canon>`** in the last commit. Ask first, after the person has compared `spry status`
    with writ's last ledger. The trail and git history keep everything.
