# spry — design

> **Status:** draft for review · **Owner:** Chetan · **Audience:** 8/10 (the people building spry)
> **Relation to writ:** inspired by, not based on. Same aim — agent-first development that a human
> team can follow — rebuilt around what running writ on two real projects taught.

## 1. Principles

- **One parent per item.** Milestone → Epic → Feature → Story → Slice, each link one-to-many. No
  many-to-many anywhere in the plan.
- **Status is derived, never typed.** Humans write intent; the tool computes done/total.
- **Written for its reader.** Every document type declares an audience level; planning is
  non-technical, slicing is technical — in the files and in the chat.
- **Incremental.** No up-front BRD. Plan one milestone, then one epic, then one feature, as needed.
- **Checked or not written.** A rule that matters is in `spry check`, not in prose.
- **Small files, indexed.** Anything that grows becomes `INDEX.md` + one file per item.
- **Agent-neutral.** Logic lives in templates, process files and the tool; skills are thin. State
  lives in files, never in a session — switching agent mid-slice loses nothing.
- **Same for one person or ten.** Team is a config section, not a separate setup.

## 2. This repository

```
.claude-plugin/marketplace.json   # marketplace: lists the plugins below
plugins/spry/                     # the process plugin
  .claude-plugin/plugin.json
  skills/<name>/SKILL.md          # thin entry points
  process/                        # rules every agent follows; vendored into each project
    chat.md  writing.md  conflicts.md  interview.md  planning.md  slicing.md  setup.md
    from-writ.md  merging.md  qa.md  testing.md  recording.md  audits.md  changing.md
    compacting.md  updating.md  contributing.md
    templates/                    # every document type, one file each
  tool/spry.py                    # single file, Python stdlib only, 3.10+
  stacks/                         # per-stack setup profiles (ts-node, python, generic)
plugins/spry-web/                 # later: design-system and other "how to do X" skills
tests/                            # tool tests + template checks
docs/                             # how to use spry; docs/example/ is a worked project
```

## 3. Install

- **Claude Code (default):** `claude plugin marketplace add <repo>` → `claude plugin install spry`.
- **Any other agent:** `python3 spry.py install --agent <generic|claude|cursor|gemini>`.
  `generic` writes the skills to `spry/skills/` and lists them in a generated block of `AGENTS.md`,
  so any agent that reads `AGENTS.md` (Codex among them) can run them. `claude` writes project
  skills (`.claude/skills/spry-*`, for people not using the plugin), `cursor` writes
  `.cursor/commands/spry-*.md`, `gemini` writes `.gemini/commands/spry/*.toml` (`/spry:<name>`).
  Skills that need the plugin itself (`init`, `adopt`, `update`, `contribute`) point at the path
  `install` ran from.
- **`process/` and the tool are vendored into the project** (`spry/process/`, `spry/tool/spry.py`)
  so any agent reads the same rules and CI runs without any agent. `/spry:update` keeps them current.

## 4. A project's layout

```
AGENTS.md                         # always loaded; hard budget; pointers + must-not rules
CLAUDE.md                         # one line: @AGENTS.md
spry/
  spry.config.json                # IDs, levels, team, runners, budgets
  README.md                       # entry point for humans: what's here, where to start
  plan/
    README.md                     # roadmap: the milestones
    M-1-<slug>/
      README.md                   # the milestone + generated children block
      E-1-<slug>/
        README.md
        F-1-<slug>/
          README.md               # feature spec
          S-1-<slug>/
            README.md             # story + acceptance criteria
            checks.md             # test scenarios + manual check log (QA)
            SL-1-<slug>.md        # slice: work order + close summary (developer)
          bugs/B-1-<slug>/README.md
      tasks/T-1-<slug>/README.md  # technical work with no story; its slices beside it
  knowledge/
    glossary.md                   # one term per concept; banned synonyms
    conventions/INDEX.md + <area>.md
    decisions/INDEX.md + D-<n>-<slug>.md
    external/<dependency>/INDEX.md + <behaviour>.md
    security.md  performance.md  … # interview outputs, index→item when over budget
  history/writ.md                 # adopted from writ only: old ID → new (process/from-writ.md)
  history/writ/slices/            # writ's slice summaries, as written; check skips, find lists last
  history/writ/requirements/      # writ's requirement details, as written; their content is in stories
  process/                        # vendored from the plugin: rules + templates
  tool/spry.py
.spry/                            # gitignored: search index, personal tone, gate stamp, caches
```

- **The folder tree is the hierarchy.** GitHub shows a folder's `README.md` when you open it, so a
  non-technical reader navigates milestone → epic → feature → story by clicking, with nothing to
  install. Moving an item to another parent is `git mv`; the path is the single source of truth
  for `parent`.
- **Folders for anything that can have children** (milestone … story, task, bug); a slice is a file.
- **One directory, `spry/`, excluded from deploy builds** (`.dockerignore` / build config written
  at setup). No nested repo: work order and code must land in one PR.

## 5. Items

| Type | ID default | Parent | Written by | Audience | Counts toward parent |
|---|---|---|---|---|---|
| Milestone | `M-1` | — | product | 2 | — |
| Epic | `E-1` | milestone | product | 2 | yes |
| Feature | `F-1` | epic | product | 3 | yes |
| Story | `S-1` | feature | product / QA | 3 | yes |
| Slice | `SL-1` | story, task or bug | developer | 8 | yes (story) |
| Task | `T-1` | any level above story | developer | 7 | no |
| Bug | `B-1` | feature or story | anyone | 4 | no |

- **Prefixes and levels are chosen in the interview** (suggestions above). Levels are configurable:
  a small project may drop Epic.
- **IDs are flat per-type counters**, never hierarchical (`M2.E3` breaks when work moves).
  `spry check` fails on a duplicate — two branches taking the same next number — and the later
  branch renames.
- **Acceptance criteria live only in stories**, numbered `AC-1…`, cited as `S-1/AC-1`.

### Front-matter

- Restricted subset so the stdlib can parse it: `key: value` and `key: [a, b]` only.
- Common: `id`, `title`, `state`, `owner`, `audience`, `blocked_by: []`, `related: []`.
  `parent` is implied by the folder.
- `state` for plan items: `draft` | `ready` | `dropped`. For slices: `planned` | `open` |
  `closed` | `dropped`. **`done` is never written** — it is derived (§6).
- Slices add `covers: [AC-1, AC-2]`, `branch`, `pr`.
- **A slice file has two parts:** the **Work order** (written at `slice-open`, before any code —
  summary, covers, plan, must-not, tests, demo, conflict check) and the **Close summary** (written at
  `slice-close` — what changed, falsify, follow-ups). The file is the source; the PR body is copied
  from it — work order at open, both parts at close — and never edited by hand.
- The tool builds the relationship map (hierarchy, blocked-by, related) from these; nobody
  maintains a map by hand.

## 6. Status and proof

- **Slice** done = `closed`. `slice-close` sets it in the PR's last commit, so on `main` it means merged.
- **Acceptance criterion** proven = a test whose name contains `S-1/AC-1` — inside a string on the
  line (a title, a docstring, a parametrize id), never a comment or code, which `check` warns about
  — or a `pass` as the latest row for it in the story's `checks.md`. A line that skips the test or leaves it to do
  (`it.skip`, `test.todo`, `xit`, `@pytest.mark.skip`) proves nothing. A later `fail` row un-proves it, test or not — a person
  saw it broken.
- **Story** done = all its slices done **and** every AC proven.
- **Feature / Epic / Milestone** done = all counted children done (dropped ones excluded).
- `spry status` prints, at every level, total vs completed, grouped by parent:
  milestones · epics by milestone · features by epic · stories by feature · slices by story.
- **Editing a story after slicing has started is allowed** — git history is the record. `spry check`
  warns (`check --base <ref>`, which CI passes on pull requests) when a change edits the text of an
  AC that a test already cites. A branch that changes an AC **and** code is blocked by
  `merge-check` until the slice carries `criteria_approved_by:` the story's owner — the quiet way
  to "pass" is to weaken the criterion to fit the code.

## 7. Audience and tone

- Every template has `audience: <1-10>` (1 = no technical knowledge, 10 = engineer in this
  codebase). It governs the document **and** the chat while a skill works on it.
- 1–3 plain words, no identifiers without their title, no code or paths; 4–6 names screens and
  data, no internals; 7–10 paths, types, commands.
- `/spry:tone <1-10>` sets a personal override, stored in `.spry/` (never committed).

## 8. Chat rules (`process/chat.md`)

Tone (§7) sets the vocabulary; these set the shape, at every level.

- Bullets, not prose. No preamble, recap, closing summary or restated question.
- Grouped under only the headings a reply needs: `BLOCKED` · `ASK` · `DONE` · `NEXT` · `FYI`.
- Every bullet leads with a tag in brackets:
  - **past tense for what the agent did** — `[Added]` `[Changed]` `[Fixed]` `[Ran]` `[Found]`;
  - **to-do verbs for what the user should do** — `[Review]` `[Decide]` `[Run]` `[Approve]`;
  - `[Note]` for a fact.
- Asks numbered from 1 each reply; options lettered `a`, `b`, `c`; one line per option saying why;
  exactly one `(recommended)`; the stem carries its own context so "2b" is a full answer.

## 9. Writing rules (`process/writing.md`)

- Bullets, one fact per line; the template's section order; no prose paragraphs.
- No `<!-- guide: -->` or `<placeholder>` left in a finished document (`spry check`).
- One term per concept — **glossary rule**: `knowledge/glossary.md` holds each term, its meaning
  and its banned synonyms; `spry check` fails on a banned synonym in `spry/` outside code, the glossary
  and `Conflict check` sections.
- Absolute dates; IDs with their title on first mention when audience ≤ 5.

## 10. Conflict check (`process/conflicts.md`)

Run by `milestone`, `epic`, `feature`, `story`, `task` and `slice-open` before a document goes
`ready` / `open`.

1. **Gather** — `spry related <file>` lists candidates: the parent, siblings, items sharing glossary
   terms, full-text hits on the draft's key phrases, the knowledge files in `always_check`, and —
   for a slice — every `open` slice and the files its plan touches.
2. **Read and classify** each finding: `Duplicate` · `Overlap` · `Contradiction` · `Dependency` ·
   `Scope` (outside the parent) · `Term` (glossary clash) · `Collision` (slice: same files as an
   open slice).
3. **Resolve** — `Dependency` → `blocked_by`; `Term` → glossary; `Duplicate` / `Contradiction` /
   `Scope` → an ask to the user; `Collision` → order or merge with the other slice.
4. **Record** in the document's `## Conflict check`: date, what was checked, each finding and its
   resolution. `spry check` refuses `ready` / `open` without a dated check or with a finding still
   marked `→ open`.

## 11. Size control

- **Budgets per file type in config, enforced by `spry check`.** Defaults: `AGENTS.md` 150 lines,
  any knowledge item 120, any `INDEX.md` entry one line.
- **`AGENTS.md` admission test** (written into the file): a line stays only if it is a pointer, a
  rule an agent breaks by default, or a rule that cannot be mechanised.
- **Index → item:** conventions, decisions, external behaviour, security notes. `INDEX.md` is
  generated from each item's `title` + `summary`; an agent reads the index and opens one item.
- **`spry find <query>`:** SQLite FTS5 (stdlib `sqlite3`) over `spry/` + `AGENTS.md`, one row per
  section (document title, heading, body; link targets and generated blocks left out), in
  `.spry/index.db`, refreshed per file when it changes. Falls back to plain search without FTS5.

## 12. Knowledge

- **External dependencies:** `knowledge/external/<dep>/` — one file per behaviour: what was
  observed, when, evidence, source (`documented` | `observed`), confidence, items it affects.
- **Decisions:** one file each — context, decision, rejected options, consequences.
- **Interview outputs:** security, performance, constraints, people/roles, each its own file.

## 13. Generated views

- Each item `README.md` has a marker block — `<!-- spry:children -->` … `<!-- /spry:children -->` —
  holding its children with links and done/total. Stories also get `<!-- spry:proof -->`.
- `spry/COVERAGE.md` holds a `<!-- spry:coverage -->` block: done vs defined at each level, criteria
  proven, slices, tasks and bugs; one row per milestone; stories whose slices are all closed with
  criteria still unproven; and unproven criteria cited only in a comment or code. `spry coverage`
  prints it on any branch.
- **Only CI on `main` regenerates and commits these** (`spry index`, `[skip ci]`). Branches never
  touch them, so they never conflict. `spry check` ignores block contents.
- A local `spry serve` (stdlib HTTP + minimal Markdown) is deferred; GitHub rendering comes first.

## 14. Team

```json
"team": {
  "members": [{"name": "Asha", "github": "asha", "roles": ["product"]}],
  "review": {"spry/plan/**": ["product"], "src/**": ["developer"]}
}
```

- Empty `members` = solo: nothing is routed for review.
- `CODEOWNERS` is generated from `review`. Skills read roles to decide who an item goes to.

## 15. Test speed

The rule: **a slow check runs only when its answer could have changed**, and the cheapest checks run
first so a slow one never runs only to be thrown away by a lint error.

- The interview captures the stack; the stack profile writes:
  - parallel test execution on by default;
  - an **affected-only** command used during a slice (`vitest --changed`, turbo filters,
    `pytest-testmon`, …);
  - the full suite in CI on `main` and nightly, and on demand — never by the agent as a routine
    step: not on a slice, not at close, not after a merge (the merge waits for CI on `main`).
- **`gate`** runs `spry check` → `checks.fast` (format, lint, types, cheapest first) → affected
  tests, stopping at the first failure. A pass is stamped in `.spry/green` with a fingerprint of the
  code (every file outside `checks.docs`, default `spry/**` and `**/*.md`); while it matches, the
  gate runs `check` alone. So a document fixed after the tests never re-runs them.
- **CI** follows the same order: `check` (which also prints `changed --base` → `code=true|false`),
  then fast checks, then tests — and the last two only when `code` is true. Slice close pushes once.
- `spry tests --slowest` reads JUnit XML and names the slowest tests.
- `test-all` runs the whole suite on demand, part by part (`tests.parts`), starting the local
  services (`stack`) only when they are down and stopping only what it started. Report only.
- Fewer conflicts come from §4 (one file per item) and §13 (no generated files on branches).

## 16. Falsify (kept, optimised)

Purpose: prove a slice's tests notice its safeguards — remove each, expect a failure.

- **Plan drafted by `/spry:slice-close` from the diff**, not by hand: guards, validation,
  authorisation and error branches the slice added. A person can edit it before it runs.
- **Mutations offered automatically** for each control (`falsify suggest`): a guard made *never true*,
  a comparison's boundary flipped (`>=` ↔ `>`; never `==` ↔ `!=`, and never a generic's `<…>`), a
  `throw` / `raise` / error return deleted. **Not negation:**
  negating a guard also breaks the normal path, so any test "catches" it — a false catch.
  Plan entries use writ's exact `find` / `with` form.
- **`expect` names acceptance criteria** (`S-1/AC-2`); tests are found by their names.
- **Runs only those test files**, through per-runner commands with `{files}`, using the runner's
  fail-fast flag — one failure is enough.
- **Baseline once** for the union of files; a red baseline marks the group `unreliable`.
- **Parallel in git worktrees** (`falsify.parallel`: `false`, `true` or a number; `--jobs N`):
  each worker has a detached worktree of `HEAD` outside the repository, so this tree is never
  written to. Installed dependencies (`node_modules`, `.venv`, `venv`, plus `falsify.share`) are
  symlinked in — except a pnpm package's own `node_modules`, whose links are copied so a workspace
  sibling resolves to the worktree's mutated copy, not the main tree's. **The baseline runs in a worktree**, so anything a worktree lacks shows as
  `unreliable`, never as every control `caught`. Falls back to serial when tracked files have
  uncommitted changes or a cited test file is not committed. A runner with `"parallel": false`
  (integration tests on a shared database, fixed ports) runs its controls one at a time.
- **Refuses** no-op mutations, files with uncommitted changes, and `expect`s with no test.
- **Always restores**, including on error, Ctrl-C and SIGTERM; checks the files are as committed after.
- **Every write gets a fresh, increasing mtime.** Two same-size mutations written in one second
  otherwise let size-and-mtime build caches (Python's `.pyc`) run the previous mutation's code — a
  false `caught`, found while building this.
- **`--record SL-n`** writes the results into the slice's Falsify table.
- **The diff decides what is falsified, not the agent.** `merge-check --base` runs `suggest` again
  and blocks when a control it lists has no row. The agent can add controls, never drop one; a
  control that cannot run is recorded `skipped — <reason>`.
- Result per control — `caught` · `survived` · `unreliable` · `skipped` — goes into the slice
  file. `survived` only when every group of its tests ran: one red or timed out makes it
  `unreliable`. A runner that times out is stopped with its whole process group. A survivor needs a
  new test or a written reason before the slice closes; a reason (on a survivor or a skipped
  control) is a `!` in `merge-check`, which a person accepts in the merge's one ask.

## 17. Tool — `spry.py`

| Command | Does |
|---|---|
| `check [--base <ref>]` | front-matter, IDs, placement in the tree, glossary, budgets, links, AC references, QA scenarios, conflict checks, leftover guides; with `--base`, cited ACs whose text changed |
| `status [--level]` | roll-up from §6 |
| `index` | regenerate marker blocks and `INDEX.md` files (CI on `main`) |
| `coverage` | the coverage page (§13): defined vs done, built but not proven |
| `related <file>` | conflict-check candidates (§10) |
| `next <type>` | next free ID |
| `new <type> --parent --title` | create an item from its template, next ID, right folder |
| `pr-body <slice> [--base]` | *For the reviewer* (covered ACs in words, ACs changed, falsify gaps, manual checks due), then the work order and close summary |
| `merge-check <slice> [--base]` | ready to merge? closed, PR number, every control the diff adds falsified, survivors resolved, ACs changed with code approved, covered ACs proven (else a QA follow-up), `check` clean |
| `gate [--force]` | §15 |
| `changed --base <ref>` | for CI: `code=true` when anything outside `checks.docs` changed |
| `merge-message <slice>` | the squash commit: subject, summary, `Slice:` / `Parent:` / `Covers:` trailers |
| `vendor` | copy `process/` and the tool into a project (plugin's copy only); `--diff` lists what differs |
| `scrub <file>` | private words (product, people, glossary terms, emails, URLs) left in text about to leave the project |
| `find <query>` | full-text search, best sections first (§11) |
| `falsify suggest <slice>` · `falsify run <plan>` | §16 |
| `tests --slowest` | §15 |
| `install --agent` | §3 |
| `codeowners` | §14 |
| `draw` | seeded, replayable choices for `/spry:explore` |

## 18. Skills (`spry` plugin)

| Skill | Audience | Does |
|---|---|---|
| `init` | 3 | Interview: product context, team, IDs, stack, security, performance → config, roadmap of milestones, knowledge files, CI, `AGENTS.md` |
| `milestone` | 2 | Interview to define one milestone (not its epics); conflict check |
| `epic` | 2 | Interview to define one epic under a milestone; conflict check |
| `feature` | 3 | Interview → feature spec (not its stories); conflict check |
| `story` | 3 | Interview → stories with acceptance criteria; conflict check |
| `slice` | 8 | Split a ready story / task / bug into `planned` slices: one slice is reviewable in one sitting and demos one visible change |
| `slice-open` | 8 | Work order (opening with a brief summary of what will be done), conflict check, branch, draft PR with the work order as its body; then builds — asking first only for something hard to undo |
| `slice-close` | 8 | Close summary from the diff, falsify, AC proof, done list; PR body refreshed with both parts |
| `review` | 8 | Review a PR against its work order; findings as blocker / should / nit, posted only on a yes |
| `merge` | 8 | Checks green, `merge-check`, PR body current, approval, base not moved → squash with trailers → waits for CI on main → what is unblocked |
| `bug` / `task` | 4 / 7 | Record one, attached to its parent |
| `status` | reader's | Roll-up explained at the asker's tone |
| `tone` | — | Personal audience override |
| `test-scenarios` | 4 | Scenarios in a story's `checks.md` from its ACs |
| `record` | 6–7 | A decision, convention or external behaviour, into the right index |
| `security-audit`, `prelaunch` | 8 | Standalone reviews |
| `test-all` | 8 | The whole suite on purpose, the local services managed; failures, slow and flaky tests named. Report only |
| `explore` | 8 | Seeded, replayable exploratory walk over an isolated instance; oracles are the area's ACs. Report only |
| `compact` | 7 | A file back under budget by moving sections to their owners; a pointer left, no fact lost |
| `process-change` | 7 | Change the process in every file it touches |
| `update` | 7 | Offer a project what spry gained since it was set up; port only what is chosen |
| `contribute` | 7 | Offer spry what a project built; files an issue, never a PR |
| `adopt` | 5 | Put spry around an existing codebase: survey, seed knowledge from what exists, plan from the next work; a writ project is planned from its mapping file (`process/from-writ.md`) — built with `init` |

`milestone` / `epic` / `feature` / `story` share one procedure (`process/planning.md`); each skill
only names its template and level.

## 19. From writ

| Kept | Changed | Dropped |
|---|---|---|
| Skills run the project; slice loop; work order before code; demo; falsify; decisions; chat rules; process-change; security-audit; prelaunch; test-scenarios; test-all; manual-test → `explore`; context-compact → `compact`; update; contribute; adopt | BRD → incremental milestones; registers → item folders; ledger → derived status; CLAUDE.md → AGENTS.md | many-to-many claims, `requirement-verify`, `coverage-review`, `change-request`, velocity, code graph, maintenance/cleanup |

Later: `product-docs`, `product-guide`, `spry-web` plugin.

**Adopting a writ project** (`process/from-writ.md`): writ's agent first cleans up in writ's terms
and writes `canon/to-spry.md` — the tree as titles, every traceable ID with what it becomes (`ac`,
`story`, `rule`, `knowledge`, `milestone`, `drop`) and whether it is done, unbuilt queue rows,
documents, local process changes. The person approves it; adopt builds the plan from it, gives each
built story one closed `Built under writ` slice, rewrites test citations to `S-n/AC-m` from the trail
in `spry/history/writ.md`, then retires `canon/`.

## 20. Settled

- 2026-10-08 — a person decides three things: the criteria, the merge, and anything hard to undo.
  Everything between runs without stopping, because the checks — the gate, falsify of every
  control the diff adds, citations only in test names, `merge-check` — stand in for a person
  watching each step. Slices of stories on different files run side by side in worktrees.
- 2026-10-08 — generated blocks: CI on `main` only. Slice size: agent judges against the written
  rule in §18. Story edits: allowed, warned when a cited AC changes. Falsify: serial first.
- 2026-10-08 — `adopt` is built alongside `init`, not after the pilot.
- 2026-10-08 — a slice file's parts are named `Work order` and `Close summary`; the PR body is copied
  from the file by the skills.
- 2026-10-08 — `compact` is its own skill, not part of `process-change`: files grow from slices,
  records and interviews, so the trigger is a budget, not a process change. writ's `manual-test` is
  `explore` here, so it is not confused with the manual checks in `checks.md`. writ's `survey.py`
  (history churn) is not ported; adopt reads the code.

## 21. Built

- 2026-10-08 — tool: `check`, `status`, `index`, `related`, `next`, `new`, `pr-body`, `vendor`.
- 2026-10-08 — `find`, `install --agent`, `codeowners`, `tests --slowest`, `check --base`.
- 2026-10-08 — parallel `falsify` in worktrees (§16), built before a pilot at the owner's call.
- 2026-10-08 — `falsify suggest` / `falsify run`, serial first; worktrees came in the entry above.
- 2026-10-08 — skills: `init`, `adopt`, `milestone`, `epic`, `feature`, `story`, `slice`,
  `slice-open`, `slice-close`, `status`, `tone`, `update`, `contribute`.
- 2026-10-08 — the rest of §18: `bug`, `task`, `test-scenarios`, `record`, `security-audit`,
  `prelaunch`, `process-change`; their procedures `qa.md`, `recording.md`, `audits.md`,
  `changing.md`, and *Bugs and tasks* in `planning.md`. Audit reports live in
  `spry/knowledge/audits/` (index → item); `new` also makes `checks`, `convention`, `external`, `audit`.
- **Update / contribute mechanics:** `plugins/spry/CHANGELOG.md` holds one `CH-n` entry per change a
  project may want (why · touches · adapt · migrate). A project's config holds `spry_baseline` — the
  last entry it considered — and `spry/knowledge/process-changes.md` logs its local changes and
  every entry taken, adapted or skipped, so an update keeps local changes. The tool is never changed
  locally; it is replaced whole.
- 2026-10-08 — `review` and `merge` (`process/merging.md`), with `merge-check` and `merge-message`.
  The merge rules a writ project kept in its always-loaded file now load only when merging.
- 2026-10-08 — `test-all`, `explore` and `compact` (`process/testing.md`, `process/compacting.md`),
  with `draw` in the tool (CH-2, 0.2.0).
- 2026-10-08 — review before the first pilot (CH-3, 0.3.0): setup writes the config first and can
  resume; adopt handles existing skills and decisions in one ask; `process/from-writ.md`; tool fixes
  for falsify (survivor vs red group, pnpm links, process groups, generics), `check --base` (bad
  ref, subfolder), titles in brackets, skipped tests, line numbers after generated blocks.
- 2026-10-08 — fewer ways to pass by mistake, fewer slow runs (CH-4, 0.4.0): a citation proves only
  in a test's name; `merge-check` requires every control the diff adds and the owner's approval for
  criteria changed with code, and turns reasons into a person's call; the PR body opens with a
  page for the reviewer; `gate` and `changed`, fast checks first, and tests only when code changed;
  the merge waits for CI instead of re-running the suite.
- 2026-10-09 — setup reads the trunk from the repository instead of assuming `main` (CH-5, 0.4.1).
- 2026-10-09 — a coverage page, `spry/COVERAGE.md`, and `spry coverage` (CH-6, 0.5.0).
- 2026-10-09 — adopt keeps writ's slice summaries in `spry/history/writ/slices/`; `check` skips them, `find` lists them last (CH-7, 0.6.0).
- 2026-10-09 — adopt splits writ's requirement details into stories, criteria and `checks.md` scenarios, planned by writ's agent in `to-spry.md` §7, and keeps the originals (CH-8, 0.7.0).
