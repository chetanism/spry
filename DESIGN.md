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
  hooks/hooks.json                # Claude Code hooks, each switched on in a project's config (§18)
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
.spry/                            # gitignored: search index, personal tone, gate stamp, caches, view/, pace/
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
  `merge-check`. Work is counted by it (`work`, §19); slices older than CH-40 get theirs once from
  their pull request's author (`owners --from-prs`).
- Slices add `covers: [AC-1, AC-2]`, `branch`, `pr`. A slice gets no GitHub issue (CH-52); an
  `issue:` on an older one is history.
- Plan items may add `issues: [42]` — the GitHub issues they were asked for in (§14), set by
  `link <ID> --issue 42`. `check` refuses a value that is not a number, and `issues` on a slice.
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
- **Two figures beside the count, where tasks or bugs sit under an item** — `stories 1 of 3` (the
  scope promised; left out where the count is already stories) and `all work 2 of 6` (stories,
  tasks and bugs done, out of all of them: what is left to do). Neither changes what *done* means:
  tasks and bugs never count toward their parent, so a bug filed under a finished milestone does
  not make it unfinished — it only adds to its work. `COVERAGE.md` has the same as its *All work*
  row; `serve` draws it as one bar (§13).
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
- The recommendation rests on the merits alone — the project's correctness, goal, rules, risk and
  cost — never the agent's convenience: less work, a smaller diff, no rerun, a deferral, sunk work or
  the person's apparent lean. Its line names the merit; a costlier best option is still recommended.

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
  under it open or closed) and defined at each level, criteria proven, slices, tasks and bugs, and all the work (stories, tasks
  and bugs together, §6); the
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
  tree as it is shown (the same makers `index` uses); a sidebar holds the plan tree with done/total, a dropped item green and struck through (settled,
  not left to do);
  an item gets its breadcrumbs and front-matter as badges (PR, issue, `covers`, `blocked_by`,
  `related` as links); search is `find`. Dot-folders and `SKIP_DIRS` are never served.
  **Never a second way to write:** edits go through the skills, which run the conflict check and
  `check`. **The files stay the only source** — no database holds a document; SQLite is the
  `find` cache only, deletable at any time. Reading a big plan takes seconds on a slow disk (5 s for
  1,300 items on one pilot), so pages answer from the last read and a request more than a second
  after it reads again in the background: a change to the tree or a generated block shows once that
  read ends — at once on a small plan, seconds later on a big one; the page's own document is always
  read fresh. Raw files are served only as images, sandboxed; anything else is shown as text.
- **The work bar** — above a milestone, epic or feature with work under it, and for each top-level
  item on the home page: one bar out of all its stories, tasks and bugs, the done ones filled in a
  colour per type, and a tick where the stories alone stand. One total, so lengths compare fairly;
  two bars over each other would set percentages of different totals side by side.

## 14. Team

```json
"team": {
  "members": [{"name": "Asha", "github": "asha", "roles": ["product"]}],
  "review": {"spry/plan/**": ["product"], "src/**": ["developer"]},
  "approval": {"missing": "block", "exempt": ["asha"]}
}
```

- Empty `members` = solo: nothing is routed for review.
- **Approval at merge** (`merge-ready`, step 4): a team PR merges approved. `approval.exempt` lists
  GitHub logins whose own PRs merge without one — a lead who approves everyone else's has nobody to
  approve theirs. `approval.missing: "warn"` turns a missing approval into a `!` the person accepts
  at the ask. Changes requested blocks under either: it is an objection, not a missing approval.
- `CODEOWNERS` is generated from `review`. Skills read roles to decide who an item goes to.

### Requests in GitHub issues

- **Anyone asks, anyone discusses.** People outside the team ask for work in GitHub issues, through
  plain-words forms (`templates/issue-forms/`). Once the discussion has settled it, a planning skill
  takes the issue (`/spry:story #42`), reads it with its comments as the starting draft, leaves out
  anything private, writes the item and names the issue in `issues:`. One issue may become several
  items, and part of one may wait — said on the issue.
- **The plan is the record** from then on; a change asked for on the issue goes through the item's
  owner, never copied across.
- **The issue shows the stage** — one label, `spry:accepted` · `ready` · `in-progress` · `done` ·
  `declined`, derived from §6 like everything else, and a plain comment (audience 2–3, IDs with
  titles, links to the items) when it changes. Several items: done when every live one is.
- **spry never closes an issue**; QA closes it after testing, and a closed issue is left alone. A
  problem found then is a new bug naming the same issue.
- **`issues --sync` is idempotent**, so it runs wherever is cheap: CI on the main branch,
  `/spry:merge`, a schedule. A merge made outside the skill still reaches its issue — the per-slice
  issue it replaces depended on `/spry:merge`'s trailer, and 32 issues on the pilots stayed open.
- **Deploys are the project's:** spry knows merged, not deployed; a deploy script may post on the
  issues it shipped (`issues --json`).

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
  tests. Every fast check runs even if one fails, and the tests then do not run (`gate.keep_going`:
  `fast`, the default; `all` runs the tests anyway; `off` stops at the first failure); a failing test
  step stops the gate. A pass is stamped in `.spry/green` with a fingerprint of the
  code (every file outside `checks.docs`, default `spry/**` and `**/*.md`); while it matches, the
  gate runs `check` alone. So a document fixed after the tests never re-runs them. The gate also
  runs `check` alone when the branch — working tree included — changed only `checks.docs` since
  its merge base with `origin/<main>`, so a rebase onto others' code, or a fresh worktree, does not
  re-run steps on code the branch never touched; unsure means it runs them. When the
  affected tests fail on a timeout (`tests.retry_when`) and `tests.retry` is set, the gate runs that
  once — the same tests with no parallelism — so load on a busy machine is not a red gate; a real
  failure fails both runs.
- **A gate says where it is** (CH-69). Before its steps it prints the time they usually take
  together, and before each step its name and its usual time: the median of that step's last five
  green runs in the step log (§17). A step never timed green, or one that runs given files, gets no
  estimate. Output is written line by line even into a pipe, so a gate run in the background shows
  each step as it starts and ends.
- **One heavy run at a time** (`checks.lock`, off by default). Sessions in separate worktrees that
  start a gate or a falsify run together fill a laptop's memory, and the timeouts that follow are
  retried. With the switch on, the gate's checks and tests and `falsify run` hold one lock for as
  long as they run — a file in the system's temporary folder named after the clone's common git
  directory (`checks.lock_path` names another), so every worktree shares it. The system holds the
  lock, so it goes when the process dies. A run that waits says once who holds it and for how
  long; the wait is over before any command starts, so it never counts against a timeout, and the
  step log keeps it apart as `waited`. Commands the run starts see `SPRY_LOCK_HELD`, and a spry
  started with it set runs directly. `spry check` and a gate skipped on its stamp never wait. spry
  orders the runs; worker counts stay the project's.
- **A branch that changed only test files** (and documents) runs those files through their falsify
  runners instead of the affected tests — a test file cannot break another package's tests — and
  stamps green, marked `tests-only`, so it stands in for CI at a merge like any pass. It takes the
  long way when a changed file is not named as a test (`test_*.py`, `*_test.py`, `*.test.*`,
  `*.spec.*` — a conftest or a Go `_test.go` helper feeds tests that never name it), when any other
  file mentions one (a shared helper's importers), or when no runner takes one; `gate --full`
  always does. The changed tests get no quiet retry.
- **A red gate says why** (CH-49). The full output of every failed step goes to `.spry/gate/last.log`
  and `last.json` (git-ignored, per checkout), and the **last line** the gate prints names the failing
  steps, the failing test files and the log — so `gate | tail -1` still shows the cause. Files are
  read from vitest, jest and pytest output as the runner printed them; any other runner gets the
  path only. On the same code fingerprint and the same commands, the next gate does not run again:
  it shows that failure and says `--force` runs it. An output that looks like the machine
  (`tests.retry_when`, and `tests.load_when` — default `Failed to start forks worker`, a port in use,
  a refused connection, a missing command) is marked `load` and does run again. The record is per
  checkout. A full pass forgets the red; a fast pass forgets only the steps it ran. **`gate --failed`**
  reruns just the test files the red gate named, found in the project by their printed path and run
  through the falsify runners; it stamps nothing, so the full gate stays the proof. When every file
  passes it marks the test steps `cleared` — the full gate then runs on the same code — but a check
  that is still red stays red, and a named file it could not find (or a failing run) leaves the record
  as the red gate made it. From connect (§17): 35 of 68 full gates failed, 31 in the affected tests; 46 of
  the 47 failed gate outputs in its session logs had been cut by `tail`, and 12 reruns on unchanged code cost 55 minutes.
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

### Steps mode — one slice for a story, built in steps

> **Status:** built in CH-51 (0.40.0). From connect's "catch-up mode", which was an instruction the
> agent sometimes did not follow.

Purpose: pay a slice's fixed costs once per story, not once per slice, while keeping one task in
the agent's hands and in each reviewer's scope at a time. A slice pays the same costs whatever its
size: a work order, a claim, a draft PR, a review agent, falsify, a full gate, two CI runs and a
merge wait. In the pilots, checks took 19–26% of active time, review agents 17–19%, and waiting on
the person took up to half of the merge phase (§17). Falsify costs the same in either mode, since
it grows with the guards a diff adds, not with the number of slices.

- **One kind of slice.** A slice holds one or more steps. A slice with one step is today's slice
  and has no `### Steps` section. `slices.mode` only changes how `/spry:slice` splits a story:
  - `split` (default): one step per slice, as today.
  - `steps`: the story is planned as steps, as slices are today (a title, the criteria each
    covers, one visible change each, in build order). Then consecutive steps are packed into the
    fewest slices that fit `slices.steps.max` (default 5) and `slices.steps.max_lines` (default
    800 lines changed, documents and `checks.generated` files left out; `0` turns it off). With
    `slices.steps.step_lines` set (default `0`, off), each step is also kept under that many lines
    — the size one reviewer reads. A story over the cap gets several slices, and each of those is a
    steps slice. Steps that could be built at the same time by different people go
    into different slices, so the slices can run side by side.
- **The work order.** In a steps slice, `### Plan` is replaced by `### Steps`. Each
  `#### Step <k> · <title>` has a `Covers:` line (the slice's criteria it covers, or `—` for a
  step that only prepares) and one plan bullet per file. `check` refuses steps that are not
  numbered from 1, more steps than `slices.steps.max`, a criterion that is in `covers` but in no
  step, and a step that covers a criterion outside `covers`.
- **One commit per step, made by the tool.** `spry.py step SL-<n>` prints the next step (its
  title, covers and plan), worked out from the commits already on the branch. So a new session
  or a compacted context continues where the last one stopped, and nothing depends on the agent
  remembering. `spry.py step SL-<n> --commit` runs `gate --fast` and commits the working tree as
  `SL-<n> step <k>: <title>` with the trailer `Step: SL-<n>/<k>`. It refuses when the fast gate is
  red, when nothing changed, or when step `k` is already committed. Commits that change only
  documents (the work order, the close summary) carry no trailer.
- **Checked, not written:**
  - `check --base`, run locally on the slice's branch, warns about a code commit with no `Step:`
    trailer that is not a `fixup!` of a step commit, and about steps committed out of order or
    twice. CI checks out a detached merge ref, so it never sees these; `merge-check` does.
  - `check` refuses a `slices.mode` other than `split` or `steps`, so a typo is not quietly `split`.
  - `merge-check` blocks unless every step has exactly one commit, in order, with no `fixup!` left.
  - A slice over `slices.steps.max_lines` at close is listed in the merge's ask, for the person to
    accept, as survivors are. So is each step whose commit is over `slices.steps.step_lines`
    (CH-68), and `step --commit` names it the moment it is made, while it can still be split. Files matching `checks.generated` (a client, a schema dump, a lock
    file) are not counted: their lines are printed beside the size, never silently dropped.
  - The `session` hook (§18) names the step the branch is on. A `step_commit` hook, filtered to
    `Bash(git commit *)` on a steps branch, refuses a commit without the trailer and names
    `spry.py step --commit`. As with every hook, it fails open, and the rule stays in `check` and
    `merge-check`.
- **A red the tool can mend, it mends** (CH-59). A `checks.fast` entry may carry `fix`, the same
  tool in write mode: the formatter's. When every red check of a step's fast gate has one,
  `step --commit` runs each on the step's files (`{files}`), names the files that changed, runs
  the fast gate again and commits on its answer. A red check without one (lint, types) refuses
  the commit as before and nothing is formatted; so does a `fix` that fails or changes no file.
  With `gate.keep_going: off` the gate stops at the first red check, so the formatter may run
  before a lint error is seen. No `fix`, no change: that is the switch. `gate` itself never
  writes a file.
- **A step's own tests, by a switch** (CH-58). With `slices.steps.tests` on, `step --commit` runs
  the test files the step added or changed, after the fast checks and through their
  `falsify.runners`, as the step `step tests`. A red one refuses the commit and names the file,
  and `gate --failed` reruns it. Only those files: not the affected set, and not a file matching
  `slices.steps.tests_skip`, where a project lists the tests that need the stack. A file no
  runner takes is left to the gate and named; no runners at all refuses the commit. Off by
  default, so the next bullet holds unless a project chooses otherwise.
- **Tests once per story.** Each step runs `gate --fast` (lint, types, no tests). The affected
  tests run while building only when their answer is needed, as today. The full gate and falsify
  run once, at close, on the whole slice. Pushes happen only at close — for the review, and at its
  end with `--force-with-lease` after the fixups are folded in — so CI runs twice per slice rather
  than twice per step.
- **Review, step by step.** At close, `/spry:review` on a steps slice starts one fresh agent per
  step, all in parallel. Each agent gets only its step's diff (its step's own commit), the step's plan, its criteria and the slice's `Must not`. One
  more agent reads the whole diff for the **seams** only: what one step relies on from another
  (an interface, the shape of data, ordering, shared state), which no single step's review can
  see. `spry.py step SL-<n> --ranges` gives each agent its diff, from `origin/<branch>` when the
  branch is not checked out, since a reviewer never switches branch. Findings are verified and merged
  into the usual single ask (`reviewing.md`). Accepted fixes are `git commit --fixup=<step commit>`.
  So are tests added for falsify survivors. Never `--squash`: its message lands after the step's and
  buries the `Step:` trailer. `spry.py step SL-<n> --squash` folds the fixups in (an autosquash
  rebase, undone if it stops) before the gate, so every step is still one clean commit when a
  person reviews the PR commit by commit. Falsify keys controls by file and line at `HEAD`, which
  the rebase leaves alone.
- **The PR and the merge.** `pr-body` lists the steps under *For the reviewer*, each linked to its
  commit. The merge stays a squash: every commit on the main branch passed the full gate, so
  bisect never stops on a commit that only passed `gate --fast`. `merge-message` adds the step
  titles to the body.
- **Pace** (§17) reads a steps slice like any other. The config commit that turns the mode on is a
  dated change, so the page compares slices before and after it. The review-agent flag counts
  agents per step.
- **What it costs, and when not to use it:**
  - A larger PR for a person to read. The cap and the step commits limit this.
  - A branch that lives longer, with more rebases. Use the mode for stories whose files no open
    slice touches (`spry.py related`).
  - Nothing reaches the main branch until the last step, so it is wrong for a story whose parts
    should ship separately.
  - The agent holds one story in context for longer. The pace flag for compactions shows whether
    the cap is too high.

### Design review — the work order read before any code

> **Status:** built in CH-60 (0.49.0), behind `slices.design_review`, off by default. From issue #18.

Purpose: find a wrong shape while changing it costs a line of the work order. The review at close
asks "is this what the work order said", so a wrong data model or API shape is found after the
code exists, or not at all. And the agent decides alone what counts as hard to undo (§22, the
three decisions): nothing checked that a choice it took without asking really was easy to undo.

- **Where:** `slice-plan` always, and `slice-open` with the switch on, after the work order and the
  conflict check, before the summary is shown and before any code (`slicing.md` *Plan* step 4).
- **Who:** one new agent, as in every review (`reviewing.md` §2): never the session that wrote the
  work order, and told nothing of why it reads as it does. It gets the slice file, its parent and
  the parent's feature, `AGENTS.md`, and the decisions and conventions indexes. It edits nothing.
- **What it checks:** each choice the plan takes without asking, against *When to stop and ask*;
  what the plan assumes that no story, feature or decision says; for each choice, an option harder
  to build and better for the product; in a steps slice, what each step needs from an earlier one.
- **What comes of it:** Blocker / Should / Nit, each resting on a line. The opening agent verifies
  each. A Blocker that stands is an ask before any code — the third decision, found by a second
  reader. An accepted Should changes the work order then.
- **The record:** the work order's last section, `### Design review`, with one count line —
  `<n> Blocker, <n> Should — <n> asked` — and a line per Blocker and its answer. The section is
  added at open, like `### Steps`; the slice template does not carry it, so a project with the
  switch off sees no change.
- **The tool only reads the line.** With the switch on, `merge-check` warns when there is none
  and when fewer were asked than there were Blockers. It never blocks: the review is a reading,
  and its proof is the answers in the slice. `pace <slice>` prints the counts.
- **Cost:** one agent and about five minutes a slice. On three slices of one project it found 11
  Blockers and 44 Shoulds; each Blocker was a hard-to-undo shape taken as an easy one, and none of
  the slices had a seams Blocker at close.

## 16. Falsify (kept, optimised)

Purpose: prove a slice's tests notice its safeguards — remove each, expect a failure.

- **Plan drafted by `/spry:slice-close` from the diff**, not by hand: guards, validation,
  authorisation and error branches the slice added. A person can edit it before it runs.
- **A control is a line that refuses, stops or decides:** `if` / `else if` / `unless` / `guard`,
  `throw`, `raise`, an error return, `assert`, `require`; a clause of an `if` or `while` condition
  written over several lines; a comparison in a `WHERE` (SQL's, its `AND` / `OR` lines, a builder's
  `.where(`). An operator in an expression that only builds a value — a default, a pass-through, a
  JSX condition — is not one: about a third of one slice's controls guarded nothing.
  `falsify.controls: operators` restores the old reach, any line holding `||`, `&&` or a comparison.
- **A guard the branch only moved is not drafted:** an added line whose text the same diff removed
  elsewhere, spaces aside, once per removed copy. Its tests cite another slice's criteria, so it
  could only read `survived`. `suggest` says how many it left out.
- **Never a mutation that cannot parse.** A line is deleted only when it is a statement by itself:
  its brackets closed, nothing carried over from the line before or on to the line after, not the
  one statement of an `if` without braces. The only statement under a Python `if x:` becomes
  `pass`. Anything else is drafted `mutation: write one` with no `with`, and `run` refuses the plan
  until a person fills it — before, such a row read `unreliable — failed, but no test did`.
- **Mutations offered automatically** for each control (`falsify suggest`): a guard made *never true*,
  a comparison's boundary flipped (`>=` ↔ `>`; never `==` ↔ `!=`, and never a generic's `<…>`), a
  `throw` / `raise` / error return deleted. **Not negation:**
  negating a guard also breaks the normal path, so any test "catches" it — a false catch.
  Plan entries use writ's exact `find` / `with` form. With no such line in the diff, up to five
  lines that compute or store something are offered for deletion instead; `merge-check` never
  requires those. A branch that adds no source line at all (tests, documents) has nothing to falsify.
- **`expect` names acceptance criteria** (`S-1/AC-2`), or the bug or task for a bug's or a task's
  slice (`B-4`, `T-7`) — neither has criteria; tests are found by those IDs in their names. Or it
  names a test file by its path (one `tests.match` takes): a task's guard is often covered by a
  test that was there before the task, and names nothing.
- **Runs only those test files**, through per-runner commands with `{files}`, using the runner's
  fail-fast flag — one failure is enough.
- **Only the tests that can notice.** `suggest` drafts each control's `files`: the tests citing its
  `expect` that also name its source file. A control with `files` runs only those — a survivor
  used to run every file citing the slice's criteria, integration tests included. `files: []` —
  no citing test names the file — is reported `survived — no test names <file>` with nothing run,
  and `merge-check` blocks on that row. Without `files`, the naming tests run first and the rest
  only if those miss it; more than 20 is named `wide:` at the run.
- **Baseline once** for the union of files; a red baseline marks the group `unreliable`, and is
  said with the runner's command and its last line.
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
  sibling resolves to the worktree's mutated copy, not the main tree's. **The baseline runs in every worktree**, all at once, so anything the worktrees lack shows as
  `unreliable`, never as every control `caught`. **A slot red where another is green is left out**:
  it is broken itself, so it is named once — its command and last line — and the other slots run
  its controls; marking each of them `unreliable` said nothing about why (129 of 171 in one slice).
  A group red in every slot is the tests' own. A `"parallel": false` runner's baseline runs once,
  in one slot. Falls back to serial when tracked files have
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
  `worktrees.setup` — or `falsify.setup`, its older name — runs once in each slot before the
  baseline (create the database, migrate), with `SPRY_WORKTREE` the index of the tree the run is
  in (§24); a setup that fails stops the run — a slot that is not ready would turn every control
  after it into a result. A run made for one go, not kept, holds a lock in its folder, so
  `worktree prune` leaves it alone while it lasts.
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

## 17. Pace — where a slice's time goes

> **Status:** built in CH-44 (0.33.0); the `/spry:pace` skill in CH-47 (0.36.0); `/spry:retro`, which joins it with memory-check, in CH-48 (0.37.0); tokens, falsify outcomes and gate reruns in CH-57 (0.46.0); red checks by rule, subagents by kind, review findings and a comparison within one size in CH-61 (0.50.0); bugs filed later, by the slice that introduced them, in CH-62 (0.51.0); spend by phase in CH-76 (0.65.0), with subagents and one-call requests in CH-77 (0.66.0). Prototype: `docs/spikes/pace.py`.

Purpose: show where each slice's time and tokens went — the agent, the checks, waiting on a person —
so that person can judge what to change: the process, the config, the tests, or spry. Report only;
it never changes anything.

- **Always on, no switch.** Nothing runs while working that would not run anyway. There are two
  sources:
  - **Steps spry runs.** `gate`, `falsify run`, `check` and `merge-check` each add one JSON line to
    `.spry/pace/steps.jsonl` of the main checkout, shared by its worktrees. A line holds when it
    ran, the branch, the command and its seconds. A gate's line also holds each step's seconds,
    the code's fingerprint, whether it ran tests, and the outcome: passed, failed, skipped on the
    stamp, docs only, tests only, or a quiet retry with the seconds its first attempt took
    (`retry_lost`). For a fast check that failed it holds the rules the check's output named and
    how often (`red`), the twelve most frequent: `.spry/gate/last.log` has the whole output, but
    only until the next red gate. A falsify line holds its controls and how many were caught,
    survived and unreliable. A wait for the lock (`checks.lock`) is `waited`. Writing a line costs microseconds and never
    fails the command. The gate figures on the page come from this log, for every agent. A slice
    with no step lines (before CH-44) falls back to the gate output in the session log.
  - **The agent's session log**, read after the slice and never copied. Claude Code writes one:
    `~/.claude/projects/<dir>/*.jsonl`, with subagents' logs under `<session>/subagents/`. Each
    record has a timestamp, its `gitBranch`, its `stop_reason`, and who sent a prompt
    (`origin.kind`: human, peer, task-notification). Only these records are parsed; the rest are
    skipped by their first key. The time split needs this log: an agent that writes none gets
    gate figures but no page rows. The log format is not a stable API, so a record the tool
    cannot read is skipped, never guessed, and a log it cannot read at all is named.
  - Hooks were rejected: a hook on every tool call starts a process each time, hundreds per slice,
    and that cost is worst on a slow disk.
- **Which slice:** a log record's branch, matched to a slice's `branch:` or an `sl-<n>-` name. A
  session that changes branch is split at the change, so worktrees and parallel sessions need
  nothing more.
- **Which phase:** the skills and spry commands already in the logs mark the start of each phase.
  Skills make no extra calls to mark one. A phase set in an earlier turn does not follow the
  session to another branch, so the next slice starts in *other* until its own skill runs. The
  prototype gave all time to the last skill run, which was too coarse: the review that
  `slice-close` starts filed its gate and falsify under *review*. The gate and falsify are kinds
  of time inside each phase, not phases of their own.

  | Phase | Starts at |
  |---|---|
  | open | `slice-open` or `slice-plan` starting |
  | build | `link --pr`: the draft PR exists, or `slice-build` starting |
  | close | `slice-close` starting |
  | review | a review agent starting (an `Agent` call whose description or prompt says review) |
  | fixes | that agent's report — the last one's, when several review at once |
  | merge | `merge` starting, or `merge-check` |

- **Every second of active time gets one category:**
  - The agent, thinking and writing.
  - A tool, by kind: gate, falsify, tests outside the gate, fast checks outside the gate, spry,
    git, gh, stack, polling (`until`/`sleep` loops), or other. A chained command takes the costliest
    kind in it.
  - Waiting on you: from the end of a turn to the next prompt, or a question asked.
  - **You, busy in another session:** a wait on you while you typed a prompt in another session.
    It is still a cost, the cost of running sessions side by side, but not a slow reply.
  - Waiting on a background task: any wait while a background task or agent it started is still
    running, whoever ends the wait. Nothing waited on you then, even if you typed first.
  - **Waiting on a subagent** the session started. Claude Code starts a subagent in the
    background and hands its report back as a message from another session, so this wait read
    *waiting on another session* until CH-61. A session's own subagents are known by the ID in
    the launch notice and by the hand-back's first words. The wait counts however long it was —
    the slice was not idle — and a subagent that never reported stops counting where its own log
    ends.
  - Waiting on another session, or on a scheduled wake-up.
  - **Waiting for the check lock:** the part of a gate or falsify call spent behind another
    worktree's run (`checks.lock`). The call is matched to its step-log line — its slice, and a
    line written while it ran — and the `waited` there moves from checks to this category. A call
    with no match keeps its time, so the lock is under-counted, never over.
  - **Away:** a gap longer than `pace.away` (default 30 min) that is not a tool running. Away time is
    left out of every total.
  - Session start and `/clear` count as the end of a turn. Parallel sessions are summed, and the page
    also shows real time: the union of the active spans.
- **Tokens**, from the same session logs:
  - Each request to the model carries its usage: fresh input, cache read, cache written (kept 5
    minutes or 1 hour) and output. The log repeats it on every record of the request, so it is
    counted once per `requestId`.
  - **Spend** is in input-token equivalents: each kind times its weight in `pace.token_weights`.
    The defaults are the usual price ratios, stated as assumptions: cache read 0.1, cache write
    1.25 or 2, output 5. One number then compares slices whatever the mix; it is not money.
  - The main session and its subagents are kept apart. A subagent's requests are in its own log.
  - **Subagents by what they were started for:** build, design review, review, fix, tests or
    other — the first such word in the description Claude Code keeps beside each subagent's log
    (`subagents/*.meta.json`). Each kind has its count, its own working time and its spend. That
    time is beside the session's, not part of it: the session's part is the wait above.
  - **Context** is everything one request sent, cached or not. A slice keeps its peak, and the
    context of the first request after `slice-close` started — what every turn of the close then
    carries.
  - **By phase:** spend is also split by the phase each request fell in (open, build, close,
    review, fixes, merge, other), so a change aimed at one phase shows there (CH-76). A subagent's
    spend goes to the phase the session was in when it started (CH-77).
  - **One call a request:** of the requests that called a tool, the share that called one. Each
    request reads the whole session again, so a share over `pace.flags.lone_share` (0.9, from 20
    such requests) is flagged (CH-77).
  - **Size:** spend and active time are also shown per 100 changed lines, and each slice falls in
    a size bucket (`pace.buckets`: 300, 700, 1300, 2500 lines) so that it is set against slices
    of its own size.
- **What failed the gate:** each fast check that went red, in a fast or a full gate, and the rule
  it named — oxlint's and eslint's rule, a `TS` number, a ruff or flake8 code, a mypy code, a biome
  rule. A formatter names files, not rules, and counts as the check alone. A few rules explain
  most red gates, and each is a convention to teach or a rule to fix automatically.
- **Findings**, from the slice file and never from a log: the design review's count line (§15),
  the close review's — `### Review`, `<n> Blocker, <n> Should, <n> Nit — <n> fixed`, a line per
  review, written at `slice-close` step 5 — and the bullets under `### Choices taken` where a
  project's own process keeps that section; spry's does not ask for it. Questions put to the
  person come from the session log. `merge-check` shows the review line and never asks for it.
- **Bugs filed later** — what got past the reviews. A bug's front matter may name the slice whose
  change brought it in: `introduced_by: SL-n`, or a list when two slices made it together.
  `/spry:bug` asks once and writes it only on the person's answer; empty is allowed, and `check`
  refuses anything that is not a slice. Pace counts each bug against the slice it names, on every
  run, from the plan. A dropped bug is not counted. While no bug names a slice the count is
  unknown and shown as `–`, never as zero.
- **When it runs:** `merge-check`, once it passes, writes the slice's summary with no extra call. It
  reads only logs changed since a day before the slice's file was made, and any failure is
  swallowed, because pace never stands between a slice and its merge.
  `spry pace [<slice>] [--since <date>] [--last <n>] [--compare <point>]` runs it on demand. Each slice gets a summary,
  `.spry/pace/slices/<SL-n>.json`, written once and kept: Claude Code deletes its logs after
  `cleanupPeriodDays` (30 by default), but the numbers outlive them. Only logs that are new or
  changed (by size and mtime) are read. The prototype took 1.5–2.5 min to read 750 logs; one
  slice's logs take under a second.
- **The page**, `.spry/view/pace.md` (also in `serve`):
  - **Headline:** slices in the range, the median and slowest quarter of active time, real time
    against summed time, and each category's share.
  - **A row per slice:** active time; the agent; tools; full gates (failed) and fast gates;
    falsify; tests outside the gate; review agents (count, time); you; other sessions; sessions;
    prompts; questions asked; compactions; lines changed, with generated lines
    (`checks.generated`) beside them and not in them.
  - **By phase:** each category's share.
  - **By size:** per size bucket, the medians of active time, spend, each per 100 lines, and peak
    context; each *per 100 lines* as p25 / median / p75 once a bucket has four slices; the bugs
    filed later, in all and per slice.
  - **Subagents:** per kind, how many, in how many slices, their time, the median, the spend.
  - **Findings, a row per slice:** the design review's Blockers, Shoulds and asks; the close
    review's Blockers, Shoulds, Nits and fixes; questions asked; choices taken; the bugs filed
    later against the slice, by ID and severity.
  - **Red checks:** red runs and slices per check, then the twenty rules behind the most red runs.
  - **Tokens, falsify and reruns, a row per slice:** spend, per 100 lines, the subagents' share,
    peak context and context entering close; falsify runs, controls, caught, survived, unreliable
    and seconds a control; full gates that ran tests and how many ran on code a full gate had
    already tested; quiet retries and the time their first attempts took. Shown only when a log
    gave one of them, so an agent that writes no session log keeps the time report it had.
  - **Gate steps:** runs, total, median and max for each step; quiet retries.
  - The slowest single calls, and the calls that ran to the agent's time limit.
  - **Before and after each change.** The page marks every change it can date:
    - an entry in `spry/knowledge/process-changes.md` (written by `/spry:process-change` and
      `/spry:update`)
    - a commit that changed `spry.config.json`
    - a new `spry_baseline`

    For each change, it sets the slices closed after it against the same number closed before. It
    compares medians of active time, each category's share, gate failures, retries and waits, raw
    and per 100 changed lines, because slices differ in size — and spend, spend per 100 lines,
    peak context, context entering close, falsify controls and survivors, and reruns on unchanged
    code, fast checks failed, questions asked, the reviews' Blockers and bugs filed later per
    slice. With fewer than 10
    slices on a side it says *too few slices to tell* instead of a difference. `spry pace --compare
    <date|CH-n|commit>` does the same for any point.
  - **Within one size.** Under each change, a row per size bucket and measure — spend per 100
    lines, active time per 100 lines, context entering close — with p25 / median / p75 of the 20
    slices before and of those after. A bucket needs 10 before; one slice after is already a
    reading against them, and the table says it is not yet a difference. `spry pace <slice>` sets
    one slice against the others of its bucket the same way, from four others up. A second
    table gives each bucket's slices, bugs filed later and bugs per slice on each side, and says
    that the later side reads low until its slices have aged as long.
  - **Flags:** each is a rule with its threshold in `pace.flags`, shown with its evidence (slice,
    number) and what it usually means. Flags describe and never judge. The first set comes from
    the prototype:

  | Flag | Usually means |
  |---|---|
  | the full gate failed at close, naming the red steps | a check: fast checks were not run while building; a test step: the step's tests were not |
  | tests ran through the full gate more than once in a slice | §15 expects one full gate |
  | tests ran with no code change between them | a stamp missed: a spry bug |
  | quiet retries | the machine is overloaded by parallel sessions, or a test is flaky |
  | a call ran to the agent's time limit | a wait that belonged in the background, or a hung test |
  | waiting on another session above a share | sessions queueing behind each other |
  | waiting for the check lock above a share | other sessions' gates held it: fewer side by side, or a lighter gate |
  | waiting on you during merge above a share | the merge ask waits; merges could be batched |
  | more than three review agents | the slice is too big, or its work order unclear |
  | a compaction | the slice is too big for one context |
  | falsify above a share of the slice | `falsify.parallel` or `falsify.setup` |
  | the agent ran the whole suite | breaks §15 |

- **`/spry:pace`** (audience 7) does the judging. It runs `spry pace`; a fresh agent reads the page
  and the flagged slices, and proposes one thing per finding, with its evidence: a process change
  (`/spry:process-change`), a config change, a bug against spry (`/spry:contribute`) or against
  the project (`/spry:bug`, `/spry:task`), or nothing. Report only.
- **Stays on this machine.** `.spry/pace/` holds numbers, kinds and short command heads, never log
  text, and is never committed. Each clone sees its own sessions; a team view is left until one is
  needed. When it is, the numbers (never log text) would go into the slice file at close, behind a
  switch, on a page grouped by phase, not by person. Session logs hold everything the
  agent saw, so they are read where they are and never copied.
- **Not measured:** how long a background command ran (only the wait on it shows), a person's time
  outside the sessions, and the tests a slice added after falsify left survivors — the step log
  holds each run's counts, not which controls they were.
- **What the prototype found** (2026-10-29, spry-era slices of two pilots; 324 and 243 slices,
  median 38 and 49 min of active time):
  - The agent thinking and writing: 15% and 12%.
  - Waiting on the person: 14% and 12%, and a further 8% and 5% while they were busy in another
    session. On one pilot, waiting on them took half of the merge phase. Before background tasks
    and other sessions were split out, these read 31% and 26%.
  - Waiting on a background task (mostly review agents): 17% and 19%.
  - Checks (gate, tests, falsify): 26% and 19%.
  - Waiting on another session: 24% on one pilot, mostly at merge.
  - The full gate failed 59 and 91 times.
  - Quiet retries cost 2 h on one pilot.
  - 49 and 76 calls ran to the 10-minute limit.
  - Falsify took about 1 min a slice, and a review agent about 3 min.

## 18. Agent hooks

> **Status:** built in CH-45 (0.34.0). Claude Code only; every other agent keeps `check`, CI and
> `merge-check`, which stay the authority.

Purpose: say at the moment of the mistake what `check`, `merge-check` or a reviewer would say later.
Each hook answers something a pilot did: a slice's `pr:` was set with `sed` (SL-162, CH-19), the
agent looked for the config at the root three times (CH-19), problems in documents surfaced only at
close (SL-195, CH-31), and a criterion tests cited was edited unseen until `check --base` (pulse #2,
CH-26). Before `merge`, only the agent's memory of `merging.md` step 2 ran `merge-check` before
`gh pr merge`. `merge` does not check CI; step 1 still does.

| Key under `hooks` | When | Does |
|---|---|---|
| `session` | session start, resume, clear, compaction | tells the agent where the config and tool are, the slice this branch builds, the person's tone, which hooks are on; with `worktrees`, the worktree the session is in and whether it holds its claim (§24) |
| `session_end` | the session ends | releases the worktree claims the session holds — not on `/clear` (§24) |
| `link_fields` | an Edit or Write of a slice file; a `sed -i` or `perl -i` naming one | refuses a change to `branch`, `pr` or `owner`, naming the `link` command that sets it |
| `cited_criteria` | an Edit or Write of a story | asks the person when a criterion that a test cites (`git grep`) changes or is dropped |
| `check_edit` | after an Edit or Write of a document `check` reads | `check` of that one file by its text — front-matter, budget, placeholders, links, glossary — errors sent back to the agent |
| `merge` | `gh pr merge`, from the slice's branch | runs `merge-check` against `origin/<main>` for the slice whose `pr` or branch it names; refuses the merge on a block. From another branch the tree holds another copy of the slice, so it says nothing |
| `step_commit` | `git commit`, on a branch whose slice has `### Steps` | refuses a commit of code that is not a `--fixup` or `--amend`, naming `spry.py step --commit`; a commit of what is staged is judged by what is staged, so documents alone go through |
| `check_stop` | the agent is about to stop | with documents changed (uncommitted, or on the branch), `check`; errors send it back once; each state checked is stamped in `.spry/hooks/` and not checked again, passing or not |

- **One switch each**, `hooks.<key>` in `spry.config.json`, off when missing — a project that has
  not taken CH-45 sees nothing. `SPRY_HOOKS=off` turns all of them off for one session.
- **No process for a call it cannot be about.** §22 (2026-10-29) rejected hooks for pace because
  they start a process on every tool call. These are filtered in `hooks/hooks.json` by tool and by
  an `if` rule (`Bash(gh pr merge *)`, `Edit(**/spry/plan/**)`, `Edit(**/*.md)`), so a Bash call
  or an edit of code starts nothing. A filtered hook still reads its switch first and exits.
  `SessionStart` and `Stop` take no `if`: once the plugin is installed they start Python in every
  repository (0.2–0.5 s), which leaves at once outside a spry project.
- **Cheap where the disk is slow.** None loads the plan but `merge` and `check_stop`, which run what
  the person would run anyway: `check_edit` reads one file and the glossary; `link_fields` and
  `cited_criteria` read the file being edited (and `git grep`); `session` walks file names once.
- **The project's rules, not the plugin's.** The plugin's copy of the tool answers the hook. When the
  project's vendored copy is another version, that copy answers instead, and a copy from before
  CH-45 answers nothing.
- **Fails open.** A hook's own error, a missing Python, a timeout: the call goes through
  (`onFailure: continue`). A hook only says something sooner; it is not where a rule lives.
- **A person still decides.** `cited_criteria` asks rather than refuses: changing a built criterion
  is the story owner's call (§6), and on a code branch the slice still needs `criteria_approved_by`.
- **More hooks** belong to the project: its own `.claude/settings.json`, recorded with
  `/spry:process-change`. One every project would want goes to spry through `/spry:contribute`.

## 19. Tool — `spry.py`

| Command | Does |
|---|---|
| `check [--base <ref>]` | front-matter, IDs, placement in the tree, glossary, budgets, links, AC references, QA scenarios, conflict checks, leftover guides; with `--base`, ACs whose text changed under a test, a `checks.md` scenario or a check-log row, generated blocks the branch changed, and IDs the branch and the base both took |
| `status [--level]` | roll-up from §6 |
| `index` | regenerate marker blocks and `INDEX.md` files (CI on `main`) |
| `coverage` | the coverage page (§13): defined vs done, built but not proven |
| `backlog [--section]… [--rows] [--plain]` | the backlog page (§13): in progress, ready to build, needs slicing, blocked, needs planning; or only the sections named, at most `--rows` rows of each, and with `--plain` links as their text — what an agent choosing a slice reads |
| `done` | the done page (§13): finished stories, tasks and bugs, newest first |
| `work <owner> --since [--until] [--json]` | what one person built: their slices closed in the range under each story, task or bug, newest first; their slices being built now; closed slices with no owner or no date, named |
| `owners --from-prs <file>` | once, for slices from before CH-40: fill a missing slice `owner` from its pull request's author (`gh pr list --json number,author`), a member's name by login |
| `view [--since]` · `hooks [--remove]` | the generated pages for the working tree in `.spry/view/`; git hooks that refresh them (§13) |
| `serve [--port] [--no-open]` | browse the plan and knowledge in a browser, read-only, local only (§13) |
| `index --restore <base>` | on a branch: put back the base's copy of each generated block it changed |
| `related <file>` | conflict-check candidates (§10) |
| `next <type>` | next free ID |
| `new <type> --parent --title…` · `new --batch <file>` | create items from their templates, next IDs, right folders — several in one call, all or none; with `mint: main` the IDs are taken on the main branch in one push (§22) |
| `claim <slice>` · `release <slice>` | take a slice before opening it — on the main branch with `mint: main`, refused when someone holds it, with its `owner` — and cut its branch; give it back |
| `link <slice> [--branch] [--pr] [--owner [name]]` · `link <item> --issue <n>` | set them in the slice's front-matter; a bare `--owner` is the person at this clone. On a plan item, add an issue to its `issues:` |
| `issues [--sync [--dry-run]] [--offline] [--json]` · `issues --legacy [--close]` | each issue plan items name, its stage (§14) and whether its label shows it; `--sync` sets the label and comments when the stage changes, never closing one; `--legacy` the per-slice issues from before CH-52 still open, `--close` closes them with a comment |
| `brief <slice> [--diff]` | a slice in one call: `pr-body`'s page (a planned slice: the slice as written, with its criteria in words), then the files the branch changed (`--stat`); `--diff` adds the whole diff, for a reviewer. Without `--diff`, a `!` first when this checkout's session carries more context than `slices.fresh_context` (150k; 0 turns it off) — the open or the close starts in a fresh session; `merge-ready` says the same before its ask |
| `pr-body <slice> [--base]` | *For the reviewer* (covered ACs in words, ACs changed, falsify gaps, manual checks due), then the work order and close summary |
| `merge-check <slice> [--base]` | ready to merge? closed, an owner, PR number, every control the diff adds falsified, survivors resolved, ACs changed with code approved, covered ACs proven (else a QA follow-up), `check` clean; with `slices.design_review`, a warning when the work order has no design review or a Blocker went unasked |
| `gate [--force] [--fast] [--full] [--failed]` | §15 |
| `step <slice> [--commit] [--ranges [--head]] [--squash] [--base]` | steps mode (§15): the next step and its plan, from the branch's commits; `--commit` runs `gate --fast` — and, with `slices.steps.tests`, the test files the step added or changed — and commits it with its `Step:` trailer, first running the `fix` of the red checks when each has one; `--ranges` each step's diff and the whole one, for the review; `--squash` folds `fixup!` commits into their steps |
| `changed --base <ref>` | for CI: `code=true` when anything outside `checks.docs` changed |
| `review-check <payload> --diff [--own]` | would GitHub take this review? every anchor on lines the diff shows, suggestions closed, not overlapping and not a no-op, and only `COMMENT` on your own PR |
| `merge-message <slice>` | the squash commit: subject, summary, `Slice:` / `Parent:` / `Covers:` trailers |
| `publish <slice> open\|review\|ready [--owner]` | a slice's pull request, filed: `open` — `state: open`, branch, owner, refused when `check` refuses; the work order committed first, pushed, a draft PR opened and linked; `review` — close notes committed, pushed with `--force-with-lease`, body refreshed; `ready` — closed today, the gate, the commit with `Slice:`, pushed, body refreshed, PR marked ready. Commits only `spry/`; refuses uncommitted code |
| `merge-ready [<pr>\|<slice>] [--wait [min]]` | with `--wait`, pending checks are waited for on this machine (default 30 min), not polled by the agent. `merging.md` steps 1–5 in one report: checks (a run that started no step never ran, and the gate on the PR's head stands in), `merge-check`, the PR body refreshed when stale, approval with a team, the base not moved under the PR's files, `check --base`; then the ask and the `merge-finish` command |
| `merge-finish [<pr>\|<slice>] [--ci-local]` | on the yes, steps 7–8: CI and `merge-check` again, the squash with `merge-message` at the PR's head, this tree to the main branch, CI there when the main branch moved under the PR, the progress tables when CI left them stale, `issues --sync`, what is unblocked |
| `vendor` | copy `process/` and the tool into a project (plugin's copy only); `--diff` lists what differs |
| `scrub <file>` | private words (product, people, glossary terms, emails, URLs) left in text about to leave the project |
| `proc <file> [<section>…] [--list]` | a process file's opening and only the `##` sections named, matched by their first words — what a skill reads instead of the whole file; `--list` the headings and their sizes |
| `find <query>` | full-text search, best sections first (§11) |
| `falsify suggest <slice>` · `falsify run <plan>` | §16 |
| `tests --slowest` | §15 |
| `install --agent` | §3 |
| `codeowners` | §14 |
| `draw` | seeded, replayable choices for `/spry:explore` |
| `pace [<slice>] [--since] [--last] [--compare]` | where slices' time went (§17): the page in `.spry/view/pace.md`, or one slice in detail |
| `agent-hook <name>` | one Claude Code hook call, its payload on stdin (§18); run by `hooks/hooks.json`, not by hand |
| `worktree list \| new [name] \| claim <name\|index> \| release [name] [--force] \| home [name] \| prune [--kept]` | the worktrees sessions build in (§24) |
| `say "<text>" [--slice]` · `watch [-n s] [--once]` | a milestone line in the progress log; a panel per worktree drawn from it (§24) |
| `memory-check [--dir] [--offline] [--json]` | Claude Code's memory for this checkout: the index against its files and its budget, front-matter, dates passed on what is still to do, and the items, pull requests and issues (`gh`), commits and paths each memory names; text the repository holds, overlaps |

## 20. Skills (`spry` plugin)

| Skill | Audience | Does |
|---|---|---|
| `init` | 3 | Interview: product context, team, IDs, stack, security, performance → config, roadmap of milestones, knowledge files, CI, `AGENTS.md` |
| `milestone` | 2 | Interview to define one milestone (not its epics); conflict check |
| `epic` | 2 | Interview to define one epic under a milestone; conflict check |
| `feature` | 3 | Interview → feature spec (not its stories); conflict check |
| `story` | 3 | Interview → stories with acceptance criteria; conflict check |
| `slice` | 8 | Split a ready story / task / bug into `planned` slices: one slice is reviewable in one sitting and demos one visible change |
| `slice-open` | 8 | `slice-plan` then `slice-build` in one session — the design review only with `slices.design_review` — then stops for a fresh `slice-close` |
| `slice-plan` | 8 | Work order (opening with a brief summary of what will be done), conflict check, a review of the work order by a new agent and its accepted fixes, branch, draft PR with the work order as its body; then stops before any code — asking first only for something hard to undo |
| `slice-build` | 8 | Builds a published work order on its branch, on whichever model the person chose; stops to ask when the plan is wrong or short; commits, nothing pushed, then stops for a fresh `slice-close` |
| `slice-close` | 8 | Rebase, then the close summary from the diff, AC proof, done list; review and its fixes on the draft PR; then falsify and the gate, once; PR body refreshed with both parts |
| `review` | 8 | Fresh eyes — a new agent, never the author's session — on a slice PR (against its work order), a plan PR or item (against its parent, the code and the glossary), or any other PR; verified findings as blocker / should / nit, posted only on a yes as one inline comment per line with a suggested change for wording; `COMMENT` only on your own PR; on your own PR one answer can be *post, fix, then merge*, done by this session, never the reviewing agent (`process/reviewing.md`) |
| `merge` | 8 | `merge-ready`, the ask, then `merge-finish` — checks green — or, when CI never started, the gate on the PR's head, accepted at the ask and named in a `CI:` trailer —, `merge-check`, PR body current, approval, base not moved → squash with trailers → waits for CI on main if main moved under the PR → progress tables written when CI left them stale → what is unblocked |
| `bug` / `task` | 4 / 7 | Record one, attached to its parent |
| `status` | reader's | Roll-up explained at the asker's tone |
| `work-report` | reader's | What one person built between two dates: each story, task and bug with 2–3 lines on their part, written from the close summaries, and its slices by ID and title; what they are building now. Report only |
| `tone` | — | Personal audience override |
| `test-scenarios` | 4 | Scenarios in a story's `checks.md` from its ACs |
| `record` | 6–7 | A decision, convention or external behaviour, into the right index |
| `security-audit`, `prelaunch` | 8 | Standalone reviews |
| `pace` | 7 | Where slices' time went (§17): a fresh agent reads the page and proposes a process change, config change, bug or nothing per finding, each with its evidence. Report only |
| `test-all` | 8 | The whole suite on purpose, the local services managed; failures, slow and flaky tests named. Report only |
| `explore` | 8 | Seeded, replayable exploratory walk over an isolated instance; oracles are the area's ACs. Report only |
| `compact` | 7 | A file back under budget by moving sections to their owners; a pointer left, no fact lost |
| `retro` | 7 | `pace` and `memory-check` read together: a rule the agent keeps relearning, and slices that still lose time to it, is one finding. One proposal per finding with its evidence; a memory alone is never a finding. Report only |
| `memory-check` | 7 | Claude Code's memory checked against the repository, the plan and GitHub: keep, update or delete per memory with its evidence; obvious changes offered together, each tricky one asked alone; changes nothing until approved, commits nothing |
| `worktree` | 8 | Move the session into a worktree of its own: claim one by name or index, or make one set up by the project's script; never one another session claimed (§24) |
| `process-change` | 7 | Change the process in every file it touches |
| `update` | 7 | Offer a project what spry gained since it was set up; port only what is chosen |
| `contribute` | 7 | Offer spry what a project built; files an issue, never a PR |
| `adopt` | 5 | Put spry around an existing codebase: survey, seed knowledge from what exists, plan from the next work; a writ project is planned from its mapping file (`process/from-writ.md`) — built with `init` |

`milestone` / `epic` / `feature` / `story` share one procedure (`process/planning.md`); each skill
only names its template and level. Every plan item, with `bug` and `task`, finishes with a
`/spry:review` by a new agent before it goes `ready` (`planning.review`, default `always`; a bug
with replayable evidence skips it). Each of them, `bug` and `task` take a GitHub issue, `#42`, to plan
from (§14).

## 21. From writ

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

## 22. Settled

- 2026-10-08 — a person decides three things: the criteria, the merge, and anything hard to undo.
  Everything between runs without stopping, because the checks — the gate, falsify of every
  control the diff adds, citations only in test names, `merge-check` — stand in for a person
  watching each step. Slices of stories on different files run side by side in worktrees.
- 2026-10-08 — generated blocks: CI on `main` only. Slice size: agent judges against the written
  rule in §20. Story edits: allowed, warned when a cited AC changes. Falsify: serial first.
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
- 2026-10-29 — pace (§17) has no on/off switch, because it adds nothing at run time: spry's commands log
  their own steps, and the agent's session log is read after the slice. Hooks were rejected because they
  start a process on every tool call. The timings stay on the person's machine, never in the slice
  file: a team sees no one's numbers but its own, and there is no new conflict at merge. A team
  view waits until it is needed. Named
  `pace`, not *metering*, which reads as billing. A prototype ran on two pilots' logs before the
  design was written.
- 2026-10-29 — agent hooks (§18) say early what the checks say late; they never replace them. So a
  hook fails open, `cited_criteria` asks instead of refusing, and the rules stay in `check` and
  `merge-check`, which every agent and CI run. Each is filtered to the calls it is about, answering
  the objection to hooks for pace above; one switch per hook, because a team may want the merge
  guard and not a stop that sends the agent back.
- 2026-10-31 — memory-check (CH-46) is split like `work`: the tool settles what needs no judgement
  — the index against the files, dates, IDs, pull requests, commits, paths — and the skill reads
  what each memory claims. Either half alone fails: the tool cannot tell "queued" from "was queued",
  and an agent reading 86 memories misses a dead index line. Nothing changes before the person
  answers, because the memory is theirs and outside the repository, where no review or history
  catches a wrong delete. Obvious changes go in one ask with the agent applying them recommended;
  a tricky one is asked alone, the person editing it recommended — the person's call (2026-10-31).
  `gh` is asked once per hundred numbers through GraphQL, not once per number: Pulse's memory names
  over 200.
- 2026-11-15 — the design review is **a step of `slice-open` behind a switch, recorded in the
  slice, and warned about, not enforced** (CH-60). A step of open, not a skill of its own: it is
  worth something only before the first code, and a skill a person must remember is the
  instruction that sometimes is not followed. Off by default: it costs an agent a slice, and a
  project whose slices are small and whose shapes are settled gets little for it. A warning at
  `merge-check`, not a block: the tool can see that a count line exists, not that anyone read the
  plan, and a block would be satisfied by a line typed in. The section is added at open and is
  not in the template, so the switch off changes nothing. **Not taken:** building each step in
  its own subagent, tried on the same slices — tokens per changed line did not fall (0.28M–0.57M
  against a 0.32M median) and the opening session still reached 168k–281k of context at close.
- 2026-11-15 — the formatter's write command is **a `fix` on its `checks.fast` entry**, not a
  second list and not a guess from the check's name (CH-59). The entry already names the tool,
  so the two modes sit together, and the tool need not know which check is the formatter: a
  check with a `fix` can be mended, one without stops the commit. Only `step --commit` runs it,
  where the tool is about to commit the working tree anyway; a gate that rewrote files would
  surprise whoever ran it. The fast gate runs again afterwards, so the commit rests on checks
  that saw the formatted files: seconds of machine time against an agent's turn.
- 2026-11-15 — a step's commit runs **only the test files the step touched**, behind a switch
  that is off (CH-58). The affected set at every step would undo what steps mode saves: tests
  once per story. The files a step wrote are the ones most likely red, and they are seconds.
  Off by default because it needs `falsify.runners`, and because a project whose tests need the
  stack has to say which (`slices.steps.tests_skip`) before it helps.
- 2026-11-14 — pace counts tokens as **input-token equivalents** (CH-57), not money and not raw
  counts. Raw counts mislead: a cache read is nine-tenths of the tokens and a tenth of the cost.
  Money needs a price list per model that the tool would have to keep current. Ratios between the
  kinds of token have been the same across models, so they are the default and `pace.token_weights`
  replaces them. *Context entering close* is read from the phase `pace` already tracks, not from a
  pattern over commands as the prototype did. *Tests added after falsify* was left out: the step
  log does not say which controls a run held, and guessing from counts would be wrong for a rerun
  of the survivors alone.
- 2026-10-31 — the `/spry:pace` skill (CH-47) judges and `spry pace` measures, as `/spry:memory-check`
  and `spry memory-check` do: one skill for each tool, so the numbers can be read without the
  judging. It reads the page and `spry pace <slice>`, not a JSON form of them: the page is the one
  place the flags and their evidence already sit, and a second form would have to be kept equal to
  it. A finding needs the slices it names; with fewer than 10 a side the skill reports *too few to
  tell* and proposes nothing. Memory is not an input: a memory that repeats a process rule might
  mean the rule is unclear, but it is per person and per checkout, so it cannot carry a finding
  alone. A skill that joined the two waited until `/spry:pace` had been tried on real slices (CH-48 below built it earlier, at the person's call).
- 2026-10-31 — `/spry:retro` (CH-48) joins `/spry:pace` and `/spry:memory-check`, and replaces the
  CH-47 decision to wait. The two skills stay, each alone, because one person wants the time and
  another the memory; retro is the third, so the join is written once and neither skill grows a
  mode. The agent makes the join, not the tool: whether a memory is about the same step as a flag is
  a reading, and a mechanical map would be wrong as often as right. A memory bears on a finding
  only when a pace finding already stands on its own evidence, so memory, which is per person and per
  checkout, cannot start a proposal. A memory with no finding behind it is one line pointing at
  `/spry:memory-check`; retro never prunes. Built before a pilot had run `/spry:pace`, at the
  person's call; its proposals are to be read as drafts until one has.
- 2026-11-05 — a recommendation rests on the merits alone (CH-50). `chat.md` asked for one
  `(recommended)` and a reason per option but never said what a reason may be, so the agent's own
  convenience — less work, a smaller diff, no rerun, a follow-up — passed as one. The project's cost
  still counts; the agent's does not. Recommendations fixed in a skill before anything was found
  (`/spry:pace` and `/spry:retro` recommending every proposal) now depend on what was found, as
  `reviewing.md` already did; memory-check's presets hold because they follow from how a change was
  classed, and now say so.
- 2026-11-06 — steps mode (§15, CH-51). The mode is called `steps`, after what it does. "Fast
  lane" and "catch-up" were rejected because they suggest a lower bar or say nothing to a
  newcomer. It is a project default, with `/spry:slice` packing steps per story under a size cap,
  so one switch cannot make a story into one unreadable PR. A story over the cap gets several
  steps slices: there is one kind of slice, and today's slice is a slice with one step. Review is
  one agent per step in parallel at close plus one for the seams. Reviewing each step while the
  next is built was rejected, because a fix would land on code a later step already builds on.
  The merge stays a squash, so no commit on the main branch skipped the full gate. Being an
  instruction was not enough in connect, so the tool makes the step commits and `merge-check`
  checks them.
- 2026-11-15 — a red check's rules are **recorded by the gate, in the step log** (CH-61), not read
  from `.spry/gate/last.log` afterwards: that file holds one red run and the next one replaces
  it. Only the rule and its count are kept, never the output's text.
- 2026-11-15 — a subagent's kind comes from **its description, not its prompt** (CH-61). A fix
  agent's prompt quotes the review it fixes, so the prompt said *review* for both; the
  description is the few words the session chose for it.
- 2026-11-15 — the close review's counts are **a line in the slice, shown by `merge-check` and
  not asked for** (CH-61). Quality had no number, and the transcript is not a record: it is
  deleted after a month and says what an agent reported, not what stood once verified. No
  warning when the line is missing — the review itself is the rule, and a team whose people
  review by hand has no counts to write.
- 2026-11-15 — **`watch` lives in `spry.py`**, though it is the only command that redraws a screen
  (CH-63): the tool is one file, and a second would need its own copy, version and update. And
  **a claim never guards the main checkout**: plan-only sessions share it, and a session there
  writes plans, not code, so nothing collides that `mint: main` does not already guard.
- 2026-11-15 — **progress is written by the tool, not by the agent** (CH-63). A prototype had the
  agent call a script at each milestone; sessions forgot, and every call cost a turn. The commands
  that end a stage — a step's commit, the gate, falsify, the reviews' checks, `worktree home` —
  write their own line, and `say` is only for a milestone inside a long step.
- 2026-11-15 — the slice that introduced a bug is **a field a person fills, not one the tool
  derives** (CH-62). `git blame` on the fix names the last slice to touch a line, which is often
  not the one that made it wrong; a wrong slice spoils the count more than an empty field does.
  So the count is unknown (`–`) until a bug names a slice, and the page states that recent
  slices have had less time for their bugs to be found, in place of any correction for age.
- 2026-11-15 — a change is judged **within a size bucket, as quartiles** (CH-61). One project's
  slices ran from 200 to 7,000 lines, and spend per 100 lines fell fivefold across that range, so
  a change that moved the sizes moved every median. Ten slices before make the bucket's row;
  after the change even one slice is shown, as a reading against them and named as such.
- 2026-11-18 — **plan and build are skills of their own, and the close always starts fresh**
  (CH-78). The person picks the model per session, so a split that lets the cheaper model build
  has to be a split into sessions. `slice-plan` always runs the design review, unlike
  `slice-open`: a plan another session builds from loses its author's reasons, so its second
  reading is now or never. `slice-build` asks when the plan is short instead of filling the gap —
  the opposite of an open session, which knows why it planned what it did. `slice-open` stays,
  for one model throughout, but stops after the build like `slice-build`: the close re-reads the
  diff anyway, and carrying the build cost every close request its size, below
  `slices.fresh_context` as above it. Rejected: `model:` pinned in each skill — it overrides the
  person's choice in every project, and a pinned model may not be one they have; a config key
  for it, before anyone asked; and `slice-open` keeping its close, which left the saving to a
  threshold.

## 23. Built

- 2026-10-08 — tool: `check`, `status`, `index`, `related`, `next`, `new`, `pr-body`, `vendor`.
- 2026-10-08 — `find`, `install --agent`, `codeowners`, `tests --slowest`, `check --base`.
- 2026-10-08 — parallel `falsify` in worktrees (§16), built before a pilot at the owner's call.
- 2026-10-08 — `falsify suggest` / `falsify run`, serial first; worktrees came in the entry above.
- 2026-10-08 — skills: `init`, `adopt`, `milestone`, `epic`, `feature`, `story`, `slice`,
  `slice-open`, `slice-close`, `status`, `tone`, `update`, `contribute`.
- 2026-10-08 — the rest of §20: `bug`, `task`, `test-scenarios`, `record`, `security-audit`,
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
- 2026-10-29 — falsify of a task's slice expects the task: a `T-n` in a test's name selects it, as
  a `B-n` does for a bug. Any `expect` can also be a test file's path, for a guard an older test
  covers (CH-43, 0.32.0, from issue #6).
- 2026-10-29 — `spry pace` (CH-44, 0.33.0): where a slice's time went. Its sources are a step log
  that `gate`, `check`, `falsify run` and `merge-check` write, and Claude Code's session logs read
  after the fact. The page shows before and after each dated change, and a passing `merge-check`
  keeps the slice's numbers. The `/spry:pace` skill waits until the numbers have been checked on
  real slices.
- 2026-10-29 — agent hooks (CH-45, 0.34.0): `session`, `link_fields`, `cited_criteria`, `check_edit`,
  `merge` and `check_stop`, each switched on under `hooks` in the config, in the plugin's
  `hooks/hooks.json`, answered by `spry agent-hook` (§18). From the pilots' incidents named there.
- 2026-10-31 — `/spry:memory-check` and `spry memory-check` (CH-46, 0.35.0): Claude Code's memory
  for the checkout, audited and pruned only on the person's answer. From Pulse's memory: a
  reminder overdue since 2026-09-11, decisions whose day had passed, an index of 86 lines.
- 2026-10-31 — `/spry:pace` (CH-47, 0.36.0): a fresh agent reads `spry pace` and proposes a process
  change, config change, bug, task or nothing per finding, each with its evidence; report only.
- 2026-10-31 — `/spry:retro` (CH-48, 0.37.0): `spry pace` and `spry memory-check` read together by a
  fresh agent; a memory that bears on a pace finding sharpens its proposal, one that does not is a line.
- 2026-11-02 — a red gate says why (CH-49, 0.38.0): the output kept in `.spry/gate/last.log` with the
  failing files on the last line, no rerun on the same code, every fast check run, `gate --failed`.
  From connect's pace data (§17); model tiers by role, a slice progress log and feature-level builds
  were weighed the same day and parked: the agent's own time is 11-16% of a slice, checks 23-25%.
- 2026-11-05 — recommendations on the merits (CH-50, 0.39.0): `chat.md` names what a recommendation
  may and may not rest on; `/spry:pace` and `/spry:retro` recommend from what was found.
- 2026-11-06 — steps mode (CH-51, 0.40.0): `slices.mode: steps` packs a story's steps into as few
  slices as `slices.steps` allows; `spry step` makes each step's commit after `gate --fast` and
  names the next; review is one agent per step plus the seams; `merge-check` blocks steps missing,
  doubled, out of order, untrailered or not folded in; the `step_commit` hook. From connect's
  catch-up mode.
- 2026-11-14 — issues are requests, not slices (CH-52, 0.41.0): `slices.issue`, `issue-body` and the
  `Closes #n` trailer are gone; plan items name the issues they were asked for in `issues:`, and
  `spry issues --sync` labels and comments each open one with its stage, never closing it; issue
  forms for people outside the team; `--legacy --close` for the per-slice issues left open. From
  pulse-v2 and connect, where 32 per-slice issues outlived their slices and requests went unanswered.
- 2026-11-14 — the tool on Windows, and a budget that leaves the Falsify table out (CH-53, 0.42.0):
  the tool writes UTF-8 whatever the console's code page; test citations are sorted by path and
  line, so `index` writes the same READMEs on every file system; a slice's line budget does not
  count the rows of its tool-written `### Falsify` table. From pulse-v2's Windows users (issue #12)
  and a slice whose 357 recorded controls alone passed its budget (issue #15).
- 2026-11-14 — falsify drafts fewer controls, valid mutations and only the tests that can notice
  (CH-54, 0.43.0): a control is a line that refuses, stops or decides, not any line with an
  operator (`falsify.controls`); a guard the branch only moved is left out; a deletion that would
  not parse is drafted `write one`; each control's `files` are the citing tests that name its
  source file, and `files: []` is `survived` with nothing run. `merge-check` follows the draft.
  From one project's ten days (issue #17): 16.1 hours of falsify over 101 slices, 1,100 of 5,106
  controls `unreliable`.
- 2026-11-14 — one heavy run at a time, and a size without generated files (CH-55, 0.44.0):
  `checks.lock` makes the gate's checks and tests and `falsify run` take one lock shared by every
  worktree of a clone; `checks.generated` names files whose lines `merge-check` and `pace` count
  apart. From the same project (issue #20): 60 gate retries and 4.8 hours in ten days from runs
  that overlapped, and a slice of 7,443 lines of which 4,710 were generated.
- 2026-11-14 — a slot whose baseline is red says why once and hands its controls on (CH-56,
  0.45.0): the baseline runs in every worktree at once; a slot red where another is green is named
  with its command and last line and left out, and the others run its controls. Red in every slot
  is still `unreliable`. From issue #23: 129 of 171 controls `unreliable` in one slice, and a
  61-minute serial rerun.
- 2026-11-14 — pace shows tokens, falsify outcomes and gate reruns beside the time (CH-57,
  0.46.0): spend in input-token equivalents with the subagents apart, peak context and context
  entering close, from the session logs; falsify runs and outcomes, reruns on unchanged code and
  the time quiet retries lost, from the step log; a *By size* table per `pace.buckets`. Items 1–4
  of issue #19, where judging one process change took four one-off scripts.
- 2026-11-15 — a step's commit can run the test files the step touched (CH-58, 0.47.0):
  `slices.steps.tests`, off by default, and `slices.steps.tests_skip` for the tests that need the
  stack. From issue #27: 29% of affected-test runs red, and 54 of 91 repeated full gates after a
  red test run, each about four minutes at close-sized context.
- 2026-11-15 — a step's commit formats the step's files when format is the only red check
  (CH-59, 0.48.0): `fix` on a `checks.fast` entry. From issue #26: 28% of one project's fast
  gates red in ten days, 27 on format alone, each a turn at 200k+ tokens of context.
- 2026-11-15 — a design review of the work order before any code (CH-60, 0.49.0):
  `slices.design_review`, off by default; one new agent reads the work order at `slice-open`, a
  Blocker becomes an ask, and the counts are recorded under `### Design review` for `merge-check`
  and `pace`. From issue #18: 11 Blockers and 44 Shoulds on three slices, at about five minutes
  and one agent each.
- 2026-11-15 — pace shows what failed the gate, subagents by kind, review findings and a change
  within one size (CH-61, 0.50.0): the gate records the rules a red check named; the wait for a
  session's own subagent is no longer *another session*; the close review is recorded under
  `### Review`; `--compare` and *By size* give p25 / median / p75 per size bucket. Items 5–8 of
  issue #19.
- 2026-11-15 — a bug records the slice that introduced it, and pace counts it (CH-62, 0.51.0):
  `introduced_by: SL-n` in a bug's front matter, asked by `/spry:bug` and never guessed; `pace`
  shows the bugs on the slice's row, and `--compare` gives bugs per slice before and after a
  point, in all and per size bucket. Issue #28.
- 2026-11-15 — worktrees made and handed out by spry, and a progress view over them (CH-63,
  0.52.0): `spry.py worktree`, `/spry:worktree`, claims released by the session-end hook, falsify
  slots set up by `worktrees.setup`; a progress log the tool writes and `spry.py watch` draws.
  Issue #21.
- 2026-11-15 — watch names the story, task or bug of each slice, and when its session was cleared
  (CH-64, 0.53.0).
- 2026-11-15 — an index's generated lines do not count toward its budget (CH-66, 0.55.0): `check`
  leaves out the lines between the `spry:index` markers, as it does a slice's Falsify table. From
  a decisions index whose 292 generated entries alone passed its budget of 300.
- 2026-11-15 — progress counts the work beside the scope (CH-67, 0.56.0): `stories n of m · all
  work n of m` where tasks or bugs sit under an item, an *All work* row on the coverage page, and a
  stacked bar in `serve`. *Done* is unchanged — rejected: letting open tasks and bugs keep a parent
  not done, which would make finished milestones unfinish when a bug is filed, and move the done
  page, `blocked_by` and what `merge` reports unblocked with them. Rejected for `serve`: two
  overlapping bars, whose lengths are percentages of different totals.
- 2026-11-15 — a cap on each step, not only the slice (CH-68, 0.57.0): `slices.steps.step_lines`
  (default 0, off), warned at `step --commit` and in `merge-check`; `max_lines: 0` turns the slice
  cap off. A reviewer reads one step at a time, so the step is the size that matters once a slice
  holds several. Rejected: refusing the commit, since the size is for a person to accept, as the
  slice cap is.
- 2026-11-17 — the gate says each step as it starts, and how long it usually takes (CH-69, 0.58.0):
  the median of each step's last five green runs, from the step log; output line by line even into
  a pipe. Rejected: a periodic "still running" line, which adds noise an estimate already answers;
  and the mean, which one slow run on a busy machine pulls.
- 2026-11-17 — the merge's steps run by the tool (CH-70, 0.59.0): `merge-ready` (steps 1–5) and
  `merge-finish` (7–8); the agent keeps the ask. Some twenty commands a merge, each read back into
  the context, become two reports. `merge-finish` checks CI and `merge-check` again, since the
  `gh pr merge` hook never sees a merge the tool makes, and merges at the PR's head only. Rejected:
  one command that asks itself, since the ask is the agent's in the person's tone (`chat.md`); and
  `gh pr merge --delete-branch`, whose local half fails in a worktree.
- 2026-11-17 — a slice's pull request filed by the tool (CH-71, 0.60.0): `publish open|review|ready`
  replaces the commits, pushes and `gh` calls of `slicing.md` *Open* step 6 and *Close* steps 5 and 8.
  It commits only the plan under `spry/` and refuses while code is uncommitted. Rejected: committing
  the whole tree, which would sweep up code steps mode commits one step at a time.
- 2026-11-17 — a skill reads only the sections it needs (CH-72, 0.61.0): `proc <file> <section>…`
  prints a process file's opening and the sections named. Opening a slice read all of `slicing.md`
  (359 lines) to use about 120. Rejected: splitting the process files, which would scatter rules
  that cite each other and break every project's vendored copy.
- 2026-11-17 — a failed full gate in `pace` names its red steps (CH-73, 0.62.0), and the hint follows
  them; `--compare` counts full gates failed in tests. From one project where 77 of 87 red full gates
  failed in the affected tests and the flag sent every one to fast checks.
- 2026-11-17 — `pace` counts a wait for the check lock as its own category (CH-74, 0.63.0), with a
  `lock_share` flag. A gate that waited 20 minutes behind another worktree's counted as 20 minutes of
  checks; in one project the waits were a quarter of the gate's wall-clock time. Rejected: reading
  the wait from the gate's printed output, which a `tail` in the command cuts.
- 2026-11-18 — a team PR may merge without an approval (CH-75, 0.64.0): `team.approval.exempt` names
  the authors whose own PRs need none, and `missing: "warn"` makes a missing approval a `!`. A lead
  who approves everyone's PRs had no one to approve theirs, and `merge-ready` blocked them. Exempting
  the author, not whoever runs the merge: a lead merging a developer's PR can approve it. Changes
  requested still blocks.
- 2026-11-18 — fewer, smaller requests to the model (CH-76, 0.65.0). Read from two projects' logs:
  78% of spend was cache reads — the whole context read again on every request — at a median
  context of 155k; 96% of requests that called a tool called one; 2,400 calls polled CI or slept.
  The cost of a step is its requests times the session's size, so the change cuts both, by doing
  locally what the agent did in turns: `merge-ready --wait` waits for checks on the machine;
  `brief` gives a session or a reviewer the slice in one call; a close whose session is past
  `slices.fresh_context` starts over after `/clear`, with the slice file as the hand-off; and
  `slicing.md` asks for independent reads in one call. `pace` splits the main session's spend by
  phase to show whether it worked. Rejected: pasting the brief into a reviewer's prompt — the main
  session would pay output rates to write it; and a hook that clears the session, which an agent
  cannot do.
- 2026-11-18 — the rest of the same reading (CH-77, 0.66.0). The largest outputs that overflowed
  the agent's tool-result limit were not test runs, as guessed, but spry's own `backlog` — 141KB in
  one project, read whole to pick one row of *Ready to build* — and whole process files read by
  each reviewer. So `backlog` takes `--section`, `--rows` and `--plain`; a reviewer reads its part
  of `reviewing.md` through `proc`; the context check runs at the open and the merge as well as the
  close; and pace splits subagents' spend by phase and counts requests that called one tool.
  Rejected: shortening test output — 12 overflows in two projects, against 42 for `backlog` alone.
- 2026-11-18 — `slice-plan` and `slice-build`, and every close in a fresh session (CH-78, 0.67.0):
  plan and close on a larger model, build and merge on a smaller one, each after `/clear`.
  `brief --as` names the skill a context stop restarts; pace counts the new skills' phases.
- 2026-11-19 — a new plan item is reviewed by fresh eyes before `ready`, not offered a review after
  its commit (CH-79, 0.68.0). `planning.review: "offer"` turns it back into an offer. A bug skips it
  only with replayable evidence in its `## Evidence`, never because an agent filed it: an agent can
  type up a person's vague report just as well, and what makes a review redundant is a reproduction
  already run. Rejected: a `reviewed:` field that `check` requires, because the plan skills are the
  only path to `ready`, and the field would mean a migration for every existing item.

## 24. Worktrees and progress

> **Status:** built in CH-63 (0.52.0). Prototype: a viewer and a milestone writer kept in one
> project's main checkout, run against four live sessions.

Purpose: several agent sessions side by side, each in a worktree of its own — isolated as the
project needs, never two in one, back on a known branch between slices — and one screen that says
what each is doing, without a token spent on telling it.

- **Config — `worktrees`:** `dir` (`.claude/worktrees`, under the main checkout), `home_branch`
  (`alt{index}`; `{name}` works too), `max` (4), `setup` (a project script; empty runs nothing),
  `share` (files copied in from the main checkout, as `.env.example`), `stale_after` (12 hours).
  Without the block, `worktree` says so and stops; nothing else changes.
- **A worktree** has a name, an index from 1 to `max` and a home branch. `worktree new [name]`
  runs `git worktree add -B <home> <dir>/<name> origin/<main>` (the local branch without a
  remote), copies `share`, and runs `setup` there with `SPRY_WORKTREE` and `SPRY_WORKTREE_NAME`.
  spry knows nothing of what the script isolates — a database, ports, an `.env`. A failed set-up
  is said; the worktree stays for the person to fix. A worktree made by hand is taken as it is: the
  first claim records it, with the index its name ends in when that one is free.
- **Claims** — `.spry/worktrees/<name>.json` in the main checkout, found from every worktree
  through `git rev-parse --git-common-dir` — hold the session id, the process and the time, written
  under a file lock so two sessions cannot both win. The process is `CLAUDE_PID` when Claude Code
  runs the command, else the agent found among the command's ancestors, else its shell;
  `SPRY_SESSION_PID` overrides. The session is `CLAUDE_CODE_SESSION_ID`, else the one the
  session-start hook noted for that process. **Stale** when the process is gone or the worktree
  wrote no progress line for `stale_after` hours; a stale claim is taken and said. The
  `session_end` hook drops the session's claims, except on `/clear`, which goes on in the same
  process: the session-start hook moves the claim to the new session id (CH-65, 0.54.0). The main
  checkout is never claimed.
- **Home:** `worktree home` checks the worktree's home branch out at the main branch's head, after
  a fetch, refusing uncommitted changes. `/spry:merge` runs it after the squash, because the main
  checkout holds the main branch and a worktree cannot check it out.
- **Falsify slots** run `worktrees.setup` with `SPRY_FALSIFY_SLOT` set as well, in place of
  `falsify.setup` (§16): one script isolates a worktree and a slot the same way. `worktree prune`
  removes slot trees no run holds — those of interrupted runs, and kept ones whose checkout is
  gone; `--kept` also the warm ones — and the records of worktrees deleted by hand.
- **Progress log** — `.spry/progress/events.jsonl` in the main checkout. `step --commit`, `gate`,
  `falsify run`, `review-check`, `merge-check` and `worktree home` each append one line: time,
  worktree, branch, slice, stage, a short result (`gate red: lint`, `falsify 113 caught, 87
  survived`, `step 2 of 4 committed (abc1234)`). Over 256 KB it keeps its newest `progress.keep`
  lines (400). A line written in a claimed worktree keeps its claim fresh. `say "<text>"` adds one by
  hand. The log never fails the command that writes it.
- **`watch [-n s] [--once]`:** a panel per worktree — name, index, branch; claim; the story, task
  or bug the slice sits under, the slice, its state and step (`step 2 of 4 · <title>`, from the work order and the branch's `Step:` trailers); the last
  five lines; the time since the last, marked *quiet* past `progress.quiet` minutes (15) while the
  worktree is claimed. The main checkout shows only when it has something to show. A top line
  names the heavy-check lock's holder (`checks.lock`).
- **Transcripts, optional:** `progress.transcripts: "claude-code"` adds what each session is doing
  — working, running a command, waiting on a subagent, waiting on you, asked you a question — its
  context and its spend (`pace.token_weights`), read a little further on each redraw from the
  newest session logs of the worktree — and the time since the session's last `/clear`, which
  starts a new log, or since it started (CH-64). Off by default; other agents get the tool's lines only. A
  permission prompt reads as a long-running command; the log does not say otherwise.

