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
    from-writ.md  merging.md  reviewing.md  qa.md  testing.md  recording.md  audits.md  changing.md
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
  COVERAGE.md  BACKLOG.md  DONE.md   # generated pages: done vs defined; what to pick up next; finished
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
.spry/                            # gitignored: search index, personal tone, gate stamp, caches, view/
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
  With `mint: main` the main branch on the remote is the counter and the push is the lock: `new`
  takes the number there and merges it into the current branch, so two sessions never take one
  number. With `mint: local` (no direct commit to the main branch) `check --base` names a number
  the branch and the main branch both took, and the later branch renames.
- **Acceptance criteria live only in stories**, numbered `AC-1…`, cited as `S-1/AC-1`.

### Front-matter

- Restricted subset so the stdlib can parse it: `key: value` and `key: [a, b]` only.
- Common: `id`, `title`, `state`, `owner`, `audience`, `blocked_by: []`, `related: []`.
  `parent` is implied by the folder. An item waits on what it and everything above it names in
  `blocked_by`. `check` refuses a dropped blocker (it never finishes) and a circle — counting that
  an item is done only when what it counts is (§6), so a slice naming its own story is one.
  Filled by the conflict check (`Dependency`) and by `slice` (a slice that needs an earlier one).
- `state` for plan items: `draft` | `ready` | `dropped`. For slices: `planned` | `open` |
  `closed` | `dropped`. **`done` is never written** — it is derived (§6).
- A slice's `owner` is **who builds it**, not who planned it: set at open from the person git says
  is at the clone (their `team.members` name; solo, git's `user.name`), and required by
  `merge-check`. Work is counted by it (`work`, §17); slices older than CH-40 get theirs once from
  their pull request's author (`owners --from-prs`).
- Slices add `covers: [AC-1, AC-2]`, `branch`, `pr` — and `issue` with `slices.issue` on: a GitHub
  issue made at open from the work order, frozen and saying so; the close summary is a comment on
  it, and the merge commit's `Closes #n` closes it. `check` refuses an open slice without one.
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
  A plan over 100 lines prints only the levels that fit and says how to go deeper:
  `status <ID>` for one branch, `--level`, or `--all`.
- **Editing a story after slicing has started is allowed** — git history is the record. `spry check`
  warns (`check --base <ref>`, which CI passes on pull requests) when a change edits the text of an
  AC that a test already cites, or that its story's `checks.md` scenarios or check-log rows
  relied on and the branch left as they were. A branch that changes an AC **and** code is blocked by
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
- Grouped under only the headings a reply needs: `BLOCKED` · `DONE` · `NEXT` · `FYI` · `ASK`.
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
- `spry/COVERAGE.md` holds a `<!-- spry:coverage -->` block: done, in progress (not done, some slice
  under it open or closed) and defined at each level, criteria proven, slices, tasks and bugs; the
  same table for each milestone not done, from one level down, and one line for each done; stories whose slices are all closed with
  criteria still unproven; and unproven criteria cited only in a comment or code. `spry coverage`
  prints it on any branch.
- `spry/BACKLOG.md` holds a `<!-- spry:backlog -->` block: slices in progress (open, or a branch
  named `sl-<n>-…` exists), ready to build, items that need slicing (no slice, or criteria no slice
  covers), blocked items with what they wait on, and what needs planning (drafts, items with no
  children). **Plan order, never typed:** by top-level item; inside one, bugs, tasks, then stories,
  in tree order; slices by ID. Every row has a *Part of* column: everything above it, top level
  first, so it works for any `levels`. In-progress and ready rows have *Unblocks* — what waits on
  the slice or on something it is part of; a blocked row names each blocker with where it stands on
  this page (in progress, ready to build, …) and its owner. `slice-open` with no ID offers its first ready row — or, with `slices.pick: ask`, lists the first
  four and recommends none. Every table numbers its rows from 1, and every row has a *Type*: story, task or bug — for a slice, what it builds;
  above those, the level (`feature`, …).
- `spry/DONE.md` holds a `<!-- spry:done -->` block: every finished story, task and bug, newest
  first — `#`, item, type, *Part of*, and *Closed*: the latest `closed:` date of the slices it
  counts. **The date is in the slice file, never read from git**: CI's checkout is shallow, and the
  same tree must give the same page in every clone. `slice-close` sets `closed:` beside
  `state: closed`; `merge-check` blocks without it, and `check` refuses one that is not a date. A
  slice closed before CH-25 has none, so its item shows `—` and sorts last, in plan order.
- **On a branch the committed pages show the main branch** as of CI's last run. `spry view` writes
  every page for the working tree to `.spry/view/` (gitignored); `spry hooks` (opt-in, per clone) runs it
  after a checkout or pull that changed `spry/` or a test. `check --base` refuses a generated block
  a branch changed — unless it matches the base now or where the branch forked — and
  `index --restore <base>` puts the base's copy back.
- **Only the main branch gets these**, written by CI (`spry index`, `[skip ci]`), or by
  `/spry:merge` when CI left them stale (`merging.md` step 8). Branches never touch them, so they never conflict. `spry check` ignores block contents.
- **`spry serve` browses the plan in a browser** — optional, read-only, on `127.0.0.1` only (any
  other `Host` header gets 403, so a page elsewhere cannot rebind a name to it and read the plan).
  Standard library only: `http.server` and a small Markdown renderer covering what spry's documents
  use, escaping all HTML but the tags GitHub allows. A page is a document under the project root at
  its own path, so relative links work as on GitHub; its generated blocks are built for the working
  tree as it is shown (the same makers `index` uses); a sidebar holds the plan tree with done/total;
  an item gets its breadcrumbs and front-matter as badges (PR, issue, `covers`, `blocked_by`,
  `related` as links); search is `find`. Dot-folders and `SKIP_DIRS` are never served.
  **Never a second way to write:** edits go through the skills, which run the conflict check and
  `check`. **The files stay the only source** — no database holds a document; SQLite is the
  `find` cache only, deletable at any time. Reading a big plan takes seconds on a slow disk (5 s for
  1,300 items on one pilot), so pages answer from the last read and a request more than a second
  after it reads again in the background: a change to the tree or a generated block shows once that
  read ends — at once on a small plan, seconds later on a big one; the page's own document is always
  read fresh. Raw files are served only as images, sandboxed; anything else is shown as text.

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
    step: not on a slice, not at close, not after a merge (the merge waits for CI on `main` only when `main` moved under the PR).
- **`gate`** runs `spry check` → `checks.fast` (format, lint, types, cheapest first) → affected
  tests, stopping at the first failure. A pass is stamped in `.spry/green` with a fingerprint of the
  code (every file outside `checks.docs`, default `spry/**` and `**/*.md`); while it matches, the
  gate runs `check` alone. So a document fixed after the tests never re-runs them. The gate also
  runs `check` alone when the branch — working tree included — changed only `checks.docs` since
  its merge base with `origin/<main>`, so a rebase onto others' code, or a fresh worktree, does not
  re-run steps on code the branch never touched; unsure means it runs them. When the
  affected tests fail on a timeout (`tests.retry_when`) and `tests.retry` is set, the gate runs that
  once — the same tests with no parallelism — so load on a busy machine is not a red gate; a real
  failure fails both runs.
- **A branch that changed only test files** (and documents) runs those files through their falsify
  runners instead of the affected tests — a test file cannot break another package's tests — and
  stamps green, marked `tests-only`, so it stands in for CI at a merge like any pass. It takes the
  long way when a changed file is not named as a test (`test_*.py`, `*_test.py`, `*.test.*`,
  `*.spec.*` — a conftest or a Go `_test.go` helper feeds tests that never name it), when any other
  file mentions one (a shared helper's importers), or when no runner takes one; `gate --full`
  always does. The changed tests get no quiet retry.
- **`tests.always`** — commands that run after the tests on every gate that runs tests, whatever code
  changed, and after the affected tests in CI: checks that read the whole code tree (banned words,
  licences), which the affected run picks up only when their own package changes.
- **`gate --fast`** runs `check` and `checks.fast` only, and stamps nothing — for each change while
  building, and for review fixes at close. The full gate runs once per slice, at close.
- **CI** follows the same order: `check` (which also prints `changed --base` → `code=true|false`),
  then fast checks, then tests — and the last two only when `code` is true. Slice close pushes twice: once for the review, once at its end.
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
  Plan entries use writ's exact `find` / `with` form. With no such line in the diff, up to five
  lines that compute or store something are offered for deletion instead; `merge-check` never
  requires those. A branch that adds no source line at all (tests, documents) has nothing to falsify.
- **`expect` names acceptance criteria** (`S-1/AC-2`), or the bug for a bug's slice (`B-4`); tests
  are found by their names.
- **Runs only those test files**, through per-runner commands with `{files}`, using the runner's
  fail-fast flag — one failure is enough. Files that name the control's source file run first; the
  rest run only if those miss it. A control cited by more than 20 files is named `wide:` at the run.
- **Baseline once** for the union of files; a red baseline marks the group `unreliable`.
- **`caught` only when a test failed**, by the runner's own report — a summary line such as
  `1 failed` (pytest, vitest, jest, mocha, go, cargo, unittest, rspec, `node --test`), or the
  runner's `failed` pattern; a turbo or docker compose prefix on the line is fine. A run that exits
  non-zero with no failed test in its output (no database, a port in use, an import error, pnpm
  refusing to run) broke before any test could notice: `unreliable`, never `caught`. So is a
  unittest module that would not import and a mocha hook that failed. The limit: jest marks a
  test failed when its `beforeAll` throws, and `node --test` a file that throws as it loads — a
  slot not ready reads as a failed test there. `falsify.setup` readies the slot before any test.
- **Parallel in git worktrees** (`falsify.parallel`: `false`, `true` or a number; `--jobs N`):
  each worker has a detached worktree of `HEAD` outside the repository, so this tree is never
  written to. Installed dependencies (`node_modules`, `.venv`, `venv`, plus `falsify.share`) are
  symlinked in — except a pnpm package's own `node_modules`, whose links are copied so a workspace
  sibling resolves to the worktree's mutated copy, not the main tree's. **The baseline runs in a worktree**, so anything a worktree lacks shows as
  `unreliable`, never as every control `caught`. Falls back to serial when tracked files have
  uncommitted changes or a cited test file is not committed. A runner with `"parallel": false`
  (integration tests on a shared database, fixed ports) runs its controls one at a time.
  Commands in a worktree run with pnpm's `verify-deps-before-run` off: pnpm 11 judges borrowed
  dependencies stale and would reinstall before every run.
- **Worktrees are kept between runs** (`falsify.keep_worktrees`, default `true`), one set per
  checkout in the system's temporary folder, and reset at the start of each: checked out at `HEAD`,
  every untracked and ignored file removed — no build output from an older commit survives. A
  fresh worktree is cold: a virus scanner reads every file on its first run (16 s against 3 s on a
  Mac). A second run of the same checkout at once gets fresh ones.
- **Slots** — each worktree, or this tree when serial — see `SPRY_FALSIFY_SLOT` (1, 2, …) and
  `SPRY_FALSIFY_SLOTS` in every command, so a test can pick the slot's own database or port.
  `falsify.setup`, if set, runs once in each slot before the baseline (create the database,
  migrate); a setup that fails stops the run — a slot that is not ready would turn every control
  after it into a result.
- **Refuses** no-op mutations, files with uncommitted changes, and `expect`s with no test.
- **Always restores**, including on error, Ctrl-C and SIGTERM; checks the files are as committed after.
- **Every write gets a fresh, increasing mtime.** Two same-size mutations written in one second
  otherwise let size-and-mtime build caches (Python's `.pyc`) run the previous mutation's code — a
  false `caught`, found while building this.
- **`--record SL-n`** writes the results into the slice's Falsify table.
- **The diff decides what is falsified, not the agent.** `merge-check --base` runs `suggest` again
  and blocks when a control it lists has no row. A row is matched by the `<!-- f:… -->` key the
  run writes (a hash of file and `find`), so a row renamed in plain words still counts. The agent can add controls, never drop one; a
  control that cannot run is recorded `skipped — <reason>`.
- Result per control — `caught` · `survived` · `unreliable` · `skipped` — goes into the slice
  file. `survived` only when every group of its tests ran: one red or timed out makes it
  `unreliable`. A runner that times out is stopped with its whole process group. A survivor needs a
  new test or a written reason before the slice closes; a reason (on a survivor or a skipped
  control) is a `!` in `merge-check`, which a person accepts in the merge's one ask.

## 17. Tool — `spry.py`

| Command | Does |
|---|---|
| `check [--base <ref>]` | front-matter, IDs, placement in the tree, glossary, budgets, links, AC references, QA scenarios, conflict checks, leftover guides; with `--base`, ACs whose text changed under a test, a `checks.md` scenario or a check-log row, generated blocks the branch changed, and IDs the branch and the base both took |
| `status [--level]` | roll-up from §6 |
| `index` | regenerate marker blocks and `INDEX.md` files (CI on `main`) |
| `coverage` | the coverage page (§13): defined vs done, built but not proven |
| `backlog` | the backlog page (§13): in progress, ready to build, needs slicing, blocked, needs planning |
| `done` | the done page (§13): finished stories, tasks and bugs, newest first |
| `work <owner> --since [--until] [--json]` | what one person built: their slices closed in the range under each story, task or bug, newest first; their slices being built now; closed slices with no owner or no date, named |
| `owners --from-prs <file>` | once, for slices from before CH-40: fill a missing slice `owner` from its pull request's author (`gh pr list --json number,author`), a member's name by login |
| `view [--since]` · `hooks [--remove]` | the generated pages for the working tree in `.spry/view/`; git hooks that refresh them (§13) |
| `serve [--port] [--no-open]` | browse the plan and knowledge in a browser, read-only, local only (§13) |
| `index --restore <base>` | on a branch: put back the base's copy of each generated block it changed |
| `related <file>` | conflict-check candidates (§10) |
| `next <type>` | next free ID |
| `new <type> --parent --title…` · `new --batch <file>` | create items from their templates, next IDs, right folders — several in one call, all or none; with `mint: main` the IDs are taken on the main branch in one push (§20) |
| `claim <slice>` · `release <slice>` | take a slice before opening it — on the main branch with `mint: main`, refused when someone holds it, with its `owner` — and cut its branch; give it back |
| `link <slice> [--branch] [--pr] [--issue] [--owner [name]]` | set them in the slice's front-matter; a bare `--owner` is the person at this clone |
| `pr-body <slice> [--base]` | *For the reviewer* (covered ACs in words, ACs changed, falsify gaps, manual checks due), then the work order and close summary |
| `merge-check <slice> [--base]` | ready to merge? closed, an owner, PR number, every control the diff adds falsified, survivors resolved, ACs changed with code approved, covered ACs proven (else a QA follow-up), `check` clean |
| `gate [--force] [--fast] [--full]` | §15 |
| `changed --base <ref>` | for CI: `code=true` when anything outside `checks.docs` changed |
| `review-check <payload> --diff [--own]` | would GitHub take this review? every anchor on lines the diff shows, suggestions closed, not overlapping and not a no-op, and only `COMMENT` on your own PR |
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
| `slice-close` | 8 | Rebase, then the close summary from the diff, AC proof, done list; review and its fixes on the draft PR; then falsify and the gate, once; PR body refreshed with both parts |
| `review` | 8 | Fresh eyes — a new agent, never the author's session — on a slice PR (against its work order), a plan PR or item (against its parent, the code and the glossary), or any other PR; verified findings as blocker / should / nit, posted only on a yes as one inline comment per line with a suggested change for wording; `COMMENT` only on your own PR; on your own PR one answer can be *post, fix, then merge*, done by this session, never the reviewing agent (`process/reviewing.md`) |
| `merge` | 8 | Checks green — or, when CI never started, the gate on the PR's head, accepted at the ask and named in a `CI:` trailer —, `merge-check`, PR body current, approval, base not moved → squash with trailers → waits for CI on main if main moved under the PR → progress tables written when CI left them stale → what is unblocked |
| `bug` / `task` | 4 / 7 | Record one, attached to its parent |
| `status` | reader's | Roll-up explained at the asker's tone |
| `work-report` | reader's | What one person built between two dates: each story, task and bug with 2–3 lines on their part, written from the close summaries, and its slices by ID and title; what they are building now. Report only |
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
documents (each into spry; history only for records of what happened), local process changes,
requirement details (a file with several jobs is a feature) and test scenarios split into features, stories and `checks.md`. The person approves it; adopt builds the plan from it, gives each
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
- 2026-10-09 — the backlog is in plan order, derived — no `priority` field and no hand-kept queue,
  which writ's `SLICE-QUEUE.md` needed re-editing for. A slice branch counts as in progress, read
  from git refs (CI fetches them), not from `gh`. Fresh pages on a branch live in `.spry/view/`,
  never in the tracked file: `skip-worktree` makes a pull refuse once CI updates it.
- 2026-10-10 — parallel sessions (CH-20). The minted file reaches the slice branch by **merging the
  main branch in**, not by writing an identical copy: the branch fills the file in next, and git
  sees two different additions of one path — a conflict at every merge — unless the merge base
  holds it. The base moving mid-slice is the smaller cost. **A claim is `branch:` on a `planned`
  slice**, not `state: open`: `check` refuses an open slice without its work order and conflict
  check, which the main branch cannot have yet. `mint` defaults to `local`, so nothing pushes to
  the main branch until a project says it may.
- 2026-10-27 — a work report counts slices by `owner:` and `closed:`, never by git authors (CH-40):
  the files are the record, the same in every clone, and a squash merge's author is whoever pressed
  the button. So a slice's owner became who builds it, set at open and required at merge. Old
  slices are filled **once** from their PR's author, not looked up on every report — a lookup would
  put `gh` and the network in a read-only page for good. The summaries come from close summaries,
  not diffs: what a slice did is already written there, in words anyone can read.
- 2026-10-24 — `new`, `claim` and `release` never load the plan (CH-37). The next number, the parent
  and the slice come from file names (`git ls-tree` on the main branch, a folder walk locally); only
  the template, the glossary and the file changed are read. The pre-push `check` is of the new
  files' text — what a fresh template can get wrong — not the whole plan, which cost Pulse 20 s a
  run. A batch is all or nothing: one commit, renumbered whole on a race.

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
- 2026-10-09 — after a merge, the full suite runs only when the main branch gained code the PR's checks never saw (`changed --base <PR head>`) (CH-9, 0.7.1).
- 2026-10-09 — a backlog page, `spry/BACKLOG.md`, and `spry backlog`; `spry view`, `spry hooks`, `index --restore`, and `check --base` refusing generated blocks a branch changed (CH-10, 0.8.0).
- 2026-10-09 — backlog rows say what each item is part of, from the top level down (CH-11, 0.8.1).
- 2026-10-09 — `review` covers any PR and a solo plan item, by fresh eyes, posting one comment per line with suggested changes; `process/reviewing.md` and `review-check` (CH-12, 0.9.0). From pulse's `requirement-review`.
- 2026-10-09 — backlog rows say what they unblock, and what a blocked row waits on stands where and with whom; `slice` writes `blocked_by` between slices that need each other; `check` refuses a dropped blocker and a circle (CH-13, 0.10.0).
- 2026-10-09 — from the connect pilot (CH-14, 0.11.0): the gate retries a timeout once, quietly;
  falsify runs the tests naming the source first and names wide controls; falsify rows keep a key, so
  renaming one never forces a re-run; a test name in a generated block is not a placeholder; `ASK`
  comes last in a reply.
- 2026-10-09 — from the connect pilot (CH-15, 0.12.0): a merge when CI never ran — the gate on the
  PR's head stands in, the person accepts it at the ask, and the squash commit carries a `CI:`
  trailer; a review's first ask can be *post, fix, then merge*, one answer for the whole way.
- 2026-10-09 — from the connect pilot (CH-16, 0.13.0): `/spry:update` updates the installed plugin
  before it reads the changelog; `falsify suggest` offers value lines when no guard was added, and a
  branch adding no source line needs no falsify.
- 2026-10-09 — `status` fits a big plan in 100 lines, takes an ID for one branch, `--all` for
  everything (CH-17, 0.13.1).
- 2026-10-09 — a GitHub issue per slice, opt-in (`slices.issue`), and `slices.pick: ask` for
  `slice-open` with no ID (CH-18, 0.14.0). From connect and pulse-v2, which both kept writ's issues.
- 2026-10-09 — small fixes from the connect pilot (CH-19, 0.14.1): `link` sets a slice's `branch`,
  `pr`, `issue`; a folder's index line shows its count instead of warning; `covers` under a bug or
  task says what to do; `AGENTS.md` names where the config lives.
- 2026-10-10 — IDs and slice claims taken on the main branch (`mint: main`): `new`, `claim`,
  `release`; `check --base` names an ID taken twice (CH-20, 0.15.0). From connect.
- 2026-10-14 — adopt moves writ's documents into spry; history holds only records of what happened.
  Every case of a detail file lands somewhere, scenario files get their own table, a fresh agent
  compares each original with what it became, and reasoning moves into the decisions it explains
  (CH-21, 0.16.0). From connect, for pulse-v2.
- 2026-10-14 — falsify of a bug's slice expects the bug: a `B-n` in a test's name selects it (CH-22,
  0.16.1). From issue #1.
- 2026-10-14 — falsify works on Windows: `/` paths quoted for cmd, `taskkill /T` on a timeout, a
  junction when a symlink is refused, serial with pnpm; files are written with LF (CH-23, 0.16.2).
  From pulse-v2's Windows users.
- 2026-10-14 — a writ detail file with several jobs becomes a feature: summary, personas, fence and
  open questions go to it, each *May not* and each non-refusal blank-field outcome is a criterion,
  unsettled reconciliation rows become bugs or open questions and stay out of `Built under writ`,
  and stories from an unreviewed file stay `draft` (CH-24, 0.17.0). For pulse-v2.
- 2026-10-14 — a done page, `spry/DONE.md`, and `spry done`, dated by a slice's `closed:`; a *Type*
  column and numbered rows on every backlog table (CH-25, 0.18.0).
- 2026-10-14 — `check --base` warns when a criterion changes under its `checks.md` scenarios or
  check-log rows, not only under a test (CH-26, 0.19.0). From issue #2.
- 2026-10-14 — a scenario opens with *Type*, *Where* and *Ready*; the list is cut before steps;
  *Before you start* says who provides each thing, and what cannot be set up through the screen;
  steps say what to achieve, not what to press (CH-27, 0.20.0). From pulse-v2's writ template,
  without its Given / Expect.
- 2026-10-15 — the gate runs `check` alone when the branch changed only documents since its merge
  base with `origin/<main>`, stamp or no stamp (CH-28, 0.21.0). From issue #3.
- 2026-10-15 — `mint: main` checks out only `spry/` in its temporary worktree, with hooks off and the
  project's git config untouched (CH-29); `falsify run --record` keeps the rows a run did not touch
  (CH-30); close falsifies before the gate, so tests added for survivors need one gate, not two
  (CH-31). 0.22.0. From connect.
- 2026-10-15 — close reviews before it proves: rebase, *What changed*, proof, follow-ups, review on
  the draft PR with its fixes, then falsify and the gate once; `gate --fast` while building
  (CH-32). `/spry:merge` writes the progress tables when CI left them stale (CH-33). 0.23.0. From
  issues #4 and #5.
- 2026-10-16 — `/spry:test-all`'s description no longer says to run it before closing a slice, and
  `chat.md`'s examples match the worked example (CH-34). 0.23.1.
- 2026-10-21 — `spry serve`: the plan, knowledge and generated pages in a browser, read-only, local
  only; `index` and `serve` share one list of generated blocks (CH-35, 0.24.0). From connect and
  pulse, where browsing hundreds of folders on GitHub got slow.
- 2026-10-22 — plans deeper than Windows' 260 characters: every file call takes the `\\?\` prefix on
  Windows, a plan document that still cannot be read is a `check` error instead of a crash, `check` warns at
  a path over 200 characters, and new slugs stop at 20 (CH-36, 0.25.0). From pulse-v2's Windows users.
- 2026-10-24 — `new`, `claim` and `release` read the plan by file name and open only what they write;
  with `mint: main` the commit is made by git plumbing on the fetched tip — no worktree, no checkout
  — and checked by its text alone. `new` takes several items, a feature and its stories included, in
  one commit and one push (CH-37, 0.26.0). From pulse-v2, where a virus scanner made each file open
  cost 11 ms and one `new` a minute.
- 2026-10-26 — the coverage page counts what is in progress beside what is done: not done, and some
  slice under it open or closed. One count, not split by how far along — slices are planned a story
  at a time, so a fraction would overstate (CH-38, 0.27.0).
- 2026-10-27 — the coverage page gives each milestone the same table as the totals, from one level
  down; a done milestone is one line. The old one-row summary left out epics, features, slices,
  tasks and fixed bugs (CH-39, 0.28.0).
- 2026-10-27 — `/spry:work-report` and `spry work`: one person's slices closed in a range, under the
  story, task or bug each builds, with what they are building now. A slice's `owner` is who builds
  it — set at open (`link --owner`, `claim`), blocked at merge without one; `owners --from-prs` fills
  old slices once from their PRs (CH-40, 0.29.0).
- 2026-10-28 — a branch that changed only test files runs those files at the gate, through the
  falsify runners, not the affected tests, and stamps green marked `tests-only`; a test file another
  file mentions, one not named as a test, or one no runner takes, sends it the long way, and
  `--full` always does. The tool decides, not a flag: it already knows. `tests.always` runs
  whole-tree checks whenever tests run (CH-41, 0.30.0, from issue #11).
- 2026-10-29 — falsify counts `caught` only when a test failed, by the runner's report; a run that
  broke first is `unreliable`. Worktrees are kept between runs and reset, run with pnpm's
  dependency check off, and each slot has its number and an optional `falsify.setup` (CH-42,
  0.31.0, from issues #7, #8, #9).
