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
are titles, and adopt numbers them. Sections, in this order; `§1.n` below means section n of this
file:

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
    in §1.5 as well.
- **State**: `done` only when writ's ledger shows the ID satisfied, meaning a test cites it. Every
  other ID is `open`. Partial coverage is `open`, with `partial: <what is missing>` in Note.
- Epic, Feature and Story are titles from §1.1. Leave them blank for `knowledge`, `milestone` and
  `drop` rows, and Story blank for `rule` rows.

### 3. Work not built

Queue rows that aren't done yet, whether planned or not started:

| writ slice | Story | Note |
|---|---|---|

The row itself doesn't move, because spry opens a slice when work on it starts. What it would have
built must show up in its story's criteria. Rows that will never be built were dropped in the
clean-up and don't appear here.

### 4. Documents

One row for each file under `<canon>` that isn't a requirement detail (§1.7), a test scenario file
(§1.8), a decision record, a slice record or a work order:

| path | kind | goes to | Note |
|---|---|---|---|

`history` means the file stays only in git history. **History holds records of what happened, never
what the product is or should be**: people read spry, not writ's history. A row goes to `history`
only when its **kind** is one of these:

- `record` — changelogs, amendments, applied or rejected change requests, archives;
- `log` — logs and reviews of past work, such as a design log or coverage reviews;
- `generated` — made from code or from the registers, such as an index, a coverage page or a routes
  list;
- `writ-process` — writ's own process documents, registry and templates, once every rule still
  wanted is in §1.5;
- `register` — a register whose every row is already in §1.2, §1.3 or §1.8, such as a queue or an
  area's requirement table;
- `readme` — a README that only explains writ's layout.

Every other row has kind `content`, and **goes to** a spry destination: a path under `spry/`
(`knowledge/conventions/api.md`, `roadmap.md`), an item by its §1.1 title (a milestone, epic,
feature or story, or that story's `checks.md`), or `task: <parent>` / `bug: <parent>` for an open
backlog item, naming its parent by its §1.1 title. A file split across several places gets one row
per part, saying which part in Note. When no destination fits, the file is a question in §1.6, not
a history row.

Reasoning behind a decision that still stands moves with it: an amendment or log entry that explains
a decision in force names that decision in Note, and adopt puts it in the decision's Context (§2
step 7). Only reasoning behind dropped or superseded decisions stays in history.

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

**A file with two or more separate jobs becomes a feature**, and each job a story under it, all
added to the tree in §1.1: what the file says about the whole requirement (its summary, its
personas, its fence, its open questions) is the feature's, and only the jobs are stories. A file
with one job becomes a story under its **area's feature** — the feature in §1.1 that holds the
area's requirements without a detail file, added there when there is none — and its feature-level
parts go to that feature. When they would take that feature over its line budget, the file becomes
a feature of its own, with one story.

A feature's content can't move to `checks.md`, so it is never cut to fit: a feature that would
still run over its budget is a question in §1.6, never a summary.

One row for the file's front matter, one for its title line, then one row per `##` section of
every detail file, in file order. A section whose parts go to different places gets one row per
part, saying which part in Note; so does any paragraph after a section's table. Every story, case,
scenario and field of the file lands somewhere: nothing in it is summarised away. The file is for
people who don't build software, and in spry they will read only the features and stories.

| detail file | section | goes to | Note |
|---|---|---|---|

- **section**: the heading as written, such as `Story 3 — a different standing at each place`, or
  `front matter` or `title`.
- **goes to**, each naming a feature or story by its §1.1 title:
  - `feature: <feature>, <section>` — that section of the feature: *Summary*, *Who uses it*,
    *How it works*, *Rules* (`R-n`), *Where it appears*, *Out of scope* or *Open questions*.
  - `story: <story>` — the story's *As / I want / So that*, from the job's own *When … I want …
    so …* line.
  - `ac: <story>` — criteria of that story. Observable behaviour, and boundary and negative cases,
    are criteria too. A case that can't be reproduced by hand stays a criterion, proven by a test.
  - `checks: <story>` — scenarios in that story's `checks.md`: the steps of a job story, fields
    tables, preconditions and data. That file has no line budget, so the detail goes here. A case
    is never only a step: it is a criterion (`ac:`) first, and its steps come here.
  - `not-in-story: <story>` — *Not in this story*: a fence between two stories of one feature.
  - `notes: <story>` — the story's Notes: words, examples, which screen or route, what is built.
  - `related: <feature or story>` — `related:` and Notes. Decisions named in it become `D-n` with
    the rest.
  - `blocked_by: <story>` — what the story waits for, by §1.1 title or §1.3 row.
  - `bug: <story>` — an open bug under that story (*Reconciliation* below).
  - `glossary` — terms the file defines.
  - `history` — nothing to carry: settled reconciliation rows, an empty verification table, and
    the requirement's quoted text, which survives as the criteria. The original is kept anyway (§2
    step 3).
- **Section by section**:
  - *front matter* — `status: reviewed` makes the file's feature and stories `ready` once written;
    any other status keeps them `draft`, so the owner still reviews them in spry (Note gives the
    status). `approved_by`, or else `drafted_by`, is their `owner`. `surface` goes to the Notes of
    each story. `priority` is not carried, because spry's plan order replaces it; the rest is
    `history`.
  - *title* — the `# <ID> — <words>` line: the words title the feature, or the story of a one-job
    file, in plain words.
  - *Summary* — each part where it belongs:
    - *Covers*, what the requirement lets someone do, and a multi-job file's *When … needs to …
      so that* → `feature: …, Summary`;
    - *Not covered* → `feature: …, Out of scope`, naming the owner of each thing;
    - where people meet the job today → `feature: …, Where it appears`;
    - the normal path, step by step → `feature: …, How it works`;
    - words it defines ("words used here") → `glossary`;
    - what holds across the whole requirement, including tables of it → `feature: …, Rules`, and
      `ac:` too wherever a test or a person could show it;
    - what is built and what is not → `notes:` each story it concerns, naming the §1.3 row that
      builds the rest;
    - a one-job file's *When … needs to … so that* → `story:`.
  - *Personas* — each persona, with its relation and its **May**, to `feature: …, Who uses it`.
    Each **May not** is a permission criterion, `ac:` on the story of the act refused: who tries,
    and what they are refused. A May not is never only a note — except `—`, or one that only names
    the requirement that owns it, which is `feature: …, Out of scope`. A May that no story states and a
    person could show ("keeps reading their department's records after it closes") is `ac:` too.
  - *Mandatory and non-mandatory fields* — each table, whole, to `checks:` the story of its act.
    An act another requirement owns (*Out of scope* names it) goes, table and criteria, to that
    requirement's story; only an act nobody owns gets a story of its own in §1.1. Every outcome in the table is a
    criterion first, `ac:` on that story: a blank that is refused (and what the person is told),
    every other "if it is left blank" outcome (a default, a different meaning per kind), and every
    limit in the *Mandatory?* column (a length, a range, a format, set once and never edited). One
    that holds across several stories is `feature: …, Rules` as well. A struck-through row is
    `history` when its change is in the BRD, otherwise a §1.6 question. The line on who has no
    fields here goes to `feature: …, Who uses it`; lines about the command line go to that
    story's Notes.
  - *Preconditions and data* — `checks:` each story, at the head of its `### Before you start`
    (§1.8 adds a scenario file's table under it).
  - *Story n* — `story:` and `ac:` on its own story, or `ac:` on another story's when it is the
    same job in a different situation. Its tag places the story: `[MVP]` under the milestone that
    tag names, `[P1 — BR-…]` under the later release that holds it, as §1.1 lists it. A wait
    written beside it (*waits for branches*, *not built — change request in pull request #188*)
    is `blocked_by:` or `notes:` naming the §1.3 row; an undecided change request is also a
    `feature: …, Open questions` entry, and "needed in MVP" there keeps the story in that
    milestone.
  - *Observable behaviour* and *Boundary and negative cases* — each item `ac:` on the story whose
    act it is about. One about no single act is `ac:` on a platform story (§1.2, *nothing proves a
    rule*), and `feature: …, Rules` too. One that only says where something belongs is
    `feature: …, Out of scope`. `None — the stories cover it` is `history`.
  - *Out of scope* — `feature: …, Out of scope`, naming the feature or story that owns each thing
    (by §1.1 title); `not-in-story:` when it fences off another story of the same feature.
  - *Open questions* — each question still open goes to `feature: …, Open questions`, as one line
    `question · who answers · —`, with its answers (a), (b) indented under it as written. They are
    not copied to §1.6, so adopt doesn't wait for them: the owner answers them in spry. A question
    already answered (struck through, *closed* or *settled*) is not open: its answer is `ac:` or
    `feature: …, Rules` like any other behaviour, and the decision or CR it names goes into that
    decision's Context (§2 step 7).
  - *Reconciliation* — one row per row of it, reading later rows first. A later `holds` row whose
    *Against* is the slice in an earlier row's *Where* (or the slice that built its `CR-*`) settles
    that row, unless the later row says it doesn't. **Unsettled** means every `fix`,
    `change-request` or `open` row no later row settles, whatever its destination below.
    - `holds`, `ratified`, or settled by a later row → `history`. A `ratified` criterion is written
      as built, and its story's Notes say who ratified it and when.
    - `fix` whose slice is in §1.3 → `history`; the §1.3 row carries it, naming the criterion in
      Note.
    - `fix` whose slice is done, or `change-request` applied, with no later row → `history` when the
      slice's summary or the applied CR shows it built; otherwise a §1.6 question.
    - `fix` with no slice queued → `bug: <story>`, in plain words: what the requirement says, and
      what the build does, with `severity` and `breaks` (the criterion) in Note. A severity the
      row doesn't make clear is a §1.6 question.
    - `change-request` not yet applied, or `open` → `feature: …, Open questions`, naming the `CR-*`
      or `OPN-*` and its owner.
    - Every criterion an unsettled row names is left out of the story's `Built under writ` slice
      (§2 step 5), even when its §1.2 row is `done`: Note names the criterion.
    - Text after the table gets its own row; where it disagrees with the table, it is a §1.6
      question.
  - *Related* — each ID to `related:` of the feature or story it concerns. Its plain sentence goes
    with it: to that story's Notes, or the feature's *Rules* or *Out of scope* by what it says.
    Slices that built it go to the trail (§2 step 4); oracles (`areas.md` sections) go to
    `checks:` as a line under `### Before you start`.
  - *Verification* — a row that records a check by hand goes to `checks: <story>`, under
    `## Runs under writ` (§2 step 3), for the criterion it checked; Note gives that criterion.
    An empty table is `history`.
- The requirement's own row in §1.2 is `story` or `ac` on one of the file's stories, as usual; its
  Note names the feature and points to this table.

### 8. Test scenarios

Only when writ kept manual test scenarios: scenario files (usually `<canon>/qa/scenarios/`) or a
manual regression list. One row per scenario, in file order:

| file | scenario | story | AC | Note |
|---|---|---|---|---|

- **scenario**: its heading or ID as written, such as `S3 — correcting a department` or `MR-12`.
- **story** and **AC**: the story by its §1.1 title, and the criteria the scenario checks, as the
  writ ID of its §1.2 row or the §1.7 row it comes from. Several scenarios may check one criterion,
  and one scenario may check several, listed in AC. A scenario that checks criteria of several
  stories gets one row per story, and lands in each one's `checks.md`. A scenario that checks no
  criterion is a finding: put `new:` and the criterion, in plain words, in AC. Adopt adds it to
  the story (§2 step 3).
- A file's *Before you start* (accounts, data, who provides them, and what can't be done through
  the screen) goes, whole and as written, into each `checks.md` its scenarios land in, under
  `### Before you start`, first under `## Scenarios` — after the detail file's preconditions when
  §1.7 put them there. One section per file, never two.
- Each scenario keeps its *Type*, *Where* and *Ready* as its first line, in the template's form
  (`**Type** … · **Where** … · **Ready** …`). One that is *Not testable yet* is `**Ready** no`,
  with what it waits for, as the story or §1.3 row that builds it; Note repeats it. A *Not
  testable yet* row that names scenarios kept outside the file (in a pull request, say) is a §1.6
  question: bring them in, or drop them.
- A scenario's *Given* is a state: it goes to *Before you start*, or to a first step that reaches
  it. Its *Expect* becomes the `→ <what you should see>` of its last step. A step before it keeps
  what writ said it shows, or none.
- The file's front matter and intro go under the `checks.md` title, beside the source line (§2
  step 3): who wrote it, its `areas`, and — when `status` isn't `reviewed` — that it is a draft and
  who still has to review it. Scenarios the intro says are held back elsewhere are a §1.6 question.
  *The requirement* is `history`.
- Each *Related* line goes to `related:` of the stories; one that limits what a scenario proves
  goes under that scenario, as written.
- Recorded runs go to that `checks.md` under `## Runs under writ`. Note says how many.

## 2. Adopt from the mapping

1. **Survey** as in `setup.md`, but skip what `to-spry.md` already says.
2. **Interview** topics a–c and e–j as usual, with drafts taken from the documents in §1.4: the BRD,
   personas, and the security and performance specs. Topic d has no questions: show the tree from
   §1.1 instead.
3. **Plan.** `spry.py new --batch` top-down, in the tree's order, which is where the IDs come from —
   a whole area per call, parents named by `key` (`planning.md` §3).
   - Each `ac` row becomes one criterion row (Given / When / Then) in plain words. It keeps the
     requirement's meaning, but not its wording when that wording is technical.
   - A `story` row gets the criteria its Note names.
   - A story goes `ready` once every criterion is written, unless §1.7 keeps it `draft` because its
     detail file was never reviewed. Its `## Conflict check` reads
     `Checked <date> against: <canon>/to-spry.md, approved <date>`.
   - **Requirement details** follow §1.7, row by row: feature sections, criteria, `checks.md`
     scenarios, *Not in this story*, Notes, `related:`, bugs and glossary terms, each where its row
     says. writ IDs in the text become their spry IDs from the trail.
   - **A feature's open questions** from §1.7 go in its *Open questions* as
     `question · who answers · —`, with their answers indented under it, and the pull request
     lists them by owner. Adopt doesn't answer them.
   - **Never cut to fit.** When a story would run over its line budget, split it into stories
     under the same feature. Only steps, fields, data and preconditions move to `checks.md`, which
     has no budget; a case stays a criterion. Never summarise a case away. A feature over its
     budget is §1.7's: its own feature, or a §1.6 question.
   - **Test scenarios** follow §1.8, row by row, as `checks.md` scenarios under their criterion.
     Each heading keeps its writ name with its file: `### AC-3 · correcting a department (writ
     BR-ORG-008 S3)`, or `### AC-3, AC-5 · …` when it checks several. Scenarios
     from a §1.7 `checks:` row do the same: `(writ BR-IAM-014 Story 3)`.
   - **Runs under writ**: writ's recorded runs and manual verification rows go in a
     `## Runs under writ` section of `checks.md`, after the check log, as they were written. They
     are not check-log rows: a writ run proves nothing in spry, and a `fail` there must not
     un-prove a criterion a test proves. The next run by hand starts the check log.
   - **New criteria**: every criterion named in a §1.3 Note or a §1.8 `new:` row is added to its
     story, marked *added at adoption* in Notes.
   - **Tasks and bugs**: each §1.4 `task:` or `bug:` row, and each §1.7 `bug:` row, becomes one,
     `spry.py new task|bug`, under its parent.
   - Every feature, story, `checks.md` and knowledge page built from a writ document says where it came
     from, in one line of Notes (or under the title of a page with no Notes), linking the kept
     original or naming the path in git history:
     `From writ [BR-IAM-014](../../history/writ/requirements/BR-IAM-014.md), Stories 3–4.` The
     source is there to check against; nobody needs to open it to understand the page.
   - **Keep each detail file** by script, unchanged, at
     `spry/history/writ/requirements/<writ ID>.md`, under one first line:
     `> writ requirement detail, as written. writ IDs → [the trail](../../writ.md).`
     Every story built from it says so in Notes, with a link. `spry check` skips these files, and
     `spry find` lists them last.
4. **The trail**, `spry/history/writ.md`: one table from old to new, `| writ ID | now |`. `now` is
   one of `S-12/AC-3`, `F-2/R-1`, `D-41`, `knowledge/security.md SEC-4`, `M-2 exit` or `dropped`.
   It also maps writ milestones (`M0` → `M-1`), writ slices (to the story they built), detail
   files and scenario files (to the stories made from them), and every §1.4 file (to the spry
   pages or items it became, as a list, or `history`). Add each row when its item is made, not
   afterwards.
5. **Built work.** Every story with at least one `done` row gets one slice, titled `Built under writ`:
   - `closed:` the day writ's last slice for it was done, when writ records it; otherwise leave it
     out, and the Done page shows `—`;
   - `state: closed`, and `covers` lists the criteria from its `done` rows, less those an
     unsettled §1.7 reconciliation row names;
   - Summary links the writ slices that built it: `- Built under writ by [SL-WD2](<path>), …`;
   - Close summary reads: imported — built, reviewed and falsified under writ.
   The story counts as done once the step 6 renames make its tests cite it — and, when §1.7 kept it
   `draft`, once its owner has reviewed it and set it `ready`.

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
   4), and their old IDs go into the trail. Each §1.4 row whose Note names a decision in force adds
   its reasoning to that decision's Context, in plain words, ending `From writ <amendment or log
   entry>.`; the decision itself doesn't change.
8. **Instructions.** `CLAUDE.md` → `AGENTS.md` under the admission test.
   - writ's process rules are dropped, because spry's process replaces them.
   - Every row in §1.5 gets a row in `knowledge/process-changes.md` with `Kind: from writ`. The spry
     repository sorts each one into: already in spry, port, project-specific, or drop.
9. **writ's machinery.** One ask to remove three things:
   - writ's skills. Those with a spry counterpart: `slice-open`, `slice-close`, `test-all`,
     `test-scenarios`, `security-audit`, `prelaunch`, `process-change`, `manual-test` (→ `explore`),
     `context-compact` (→ `compact`) and `requirement-review` (→ `review`). Those spry drops on purpose: `requirement-verify`,
     `coverage-review`, `change-request`, `cleanup` and `maintenance`. Any other skill is in §1.5
     and is decided there.
   - writ's CI workflows, if there are any (`ledger`, `size`).
   - The scripts that serve only writ: the ledger, velocity and falsify.
   Skills that belong to the project alone, such as `screen`, stay, and are listed in
   `process-changes.md`.
10. **Verify.**
    - `spry check` is clean.
    - Every row of §1.2 is in the trail.
    - By script: every detail file has `front matter` and `title` rows and every `##` heading a
      row in §1.7, and every feature, story, criterion, bug and `checks.md` scenario that §1.7
      names exists. Every *May not* of a persona is a criterion, unless §1.7 sent it to *Out of
      scope*, and every reconciliation row is accounted for. Every §1.8 row has a scenario heading
      ending `(writ <file ID> <scenario>)` in its story's `checks.md`. Every §1.4 `content` row is
      in the trail with at least one page or item. Report the gaps; fix them before the pull
      request.
    - By script: every §1.4 row that goes to `history` has a kind other than `content`.
    - **Fresh eyes on the content.** A new agent — not a fork, and not the one that wrote the
      plan — reads each detail file, scenario file and split §1.4 document (the BRD, the milestone
      plan, the specs) beside the pages it became, and lists every case, field, scenario or
      sentence of meaning that is lost or changed. Fix each one before the pull request, and say
      in it how many were found and fixed.
    - The pull request asks each requirement owner to read the features and stories built from
      their files, and lists the ones left `draft` for their review.
    - The done criteria, set beside the `done` rows, differ only where the pull request explains why
      — a comment-only citation, an unsettled reconciliation row, or a story left `draft` are the
      usual reasons.
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

## Adopted before CH-21

A project whose adopt sent current content to history gets it back from git history, on a branch,
one commit per step, in one pull request:

1. `c=$(git log -1 --format=%H --diff-filter=D -- '<canon>')^` — the last commit that still had
   `<canon>`. Read `<canon>/to-spry.md` there, and the files with `git show "$c:<path>"`.
2. **Documents.** Each `history` row that §1.4 would now call `content`: move its content where
   §1.4 says, with its source line, and add the file to the trail.
3. **Reasoning.** Each amendment or log entry behind a decision still in force adds its reasoning to
   that decision's Context, as §2 step 7 says.
4. **Details and scenarios**, if writ kept them: check each against §1.7's every-case rule and
   §1.8, and add what is missing, as §2 step 3 says.
5. **Fresh eyes**, as §2 step 10, over what steps 2–4 touched.
6. The pull request lists the rows that stay in history, and why. `spry check` is clean.
