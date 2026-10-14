---
title: spry changelog
summary: Every change a spry project may want to take, newest last. /spry:update reads it; each project records the last entry it considered as spry_baseline.
audience: 7
---
# spry changelog

Read by `/spry:update`. One entry per change a project may want; newest **last**. IDs are never
reused. A project's `spry_baseline` in `spry/spry.config.json` is the last entry it has considered.

Entry format:

- `## CH-<n> · <title>`
- **Date** · **Version** — the plugin version that carries it.
- **Touches** — plugin paths: `process/…`, `tool/spry.py`, `skills/…`, `stacks/…`.
- **Why** — the failure or gap it answers.
- **Adapt** — what a project chooses when taking it, or `nothing`.
- **Migrate** — what existing documents need, or `nothing`.

## CH-1 · First release

- **Date:** 2026-10-08 · **Version:** 0.1.0
- **Touches:** everything
- **Why:** the baseline every project starts from.
- **Adapt:** nothing
- **Migrate:** nothing

## CH-2 · Full suite, exploratory testing, compaction

- **Date:** 2026-10-08 · **Version:** 0.2.0
- **Touches:** `skills/test-all`, `skills/explore`, `skills/compact`, `process/testing.md`,
  `process/compacting.md`, `process/setup.md`, `process/templates/spry.config.json`,
  `stacks/generic.md`, `tool/spry.py` (`draw`; the over-budget message names `/spry:compact`)
- **Why:** nothing ran the whole suite on purpose with the local services managed; nothing tested
  between slices, where combinations nobody wrote down live; and `spry check` reported a file over
  budget while nothing took lines out without losing facts.
- **Adapt:** the commands — `tests.parts` (optional; `tests.all` alone still works), `stack`, and
  `explore`, which may stay `<…>` until the first `/spry:explore`.
- **Migrate:** nothing

## CH-3 · Review before the first pilot

- **Date:** 2026-10-08 · **Version:** 0.3.0
- **Touches:** `process/setup.md`, `process/from-writ.md` (new), `process/conflicts.md`,
  `process/templates/{ci-github.yml,decision.md,glossary.md}`, `skills/{init,adopt,status}`,
  `stacks/{python,typescript-node}.md`, `tool/spry.py`
- **Why:**
  - Setup ran `spry.py new milestone` before it had written the config, so every init and adopt
    stopped at topic d.
  - A setup that stopped part-way could not be resumed.
  - Adopt said nothing about skills or CI that a spry skill replaces, and asked about decision
    records one at a time.
  - A writ project had no path in.
  - In the tool:
    - falsify reported `survived` when another group of tests was red or timed out;
    - falsify tested the main tree's code in a pnpm workspace;
    - falsify left a runner's children running after a timeout;
    - falsify flipped generics and equality, which is negation;
    - `check --base` said nothing when the ref could not be read, or when `spry/` sat in a
      subfolder of the repository;
    - a title starting with `[` was read as a list;
    - a skipped test proved a criterion;
    - line numbers after a generated block were wrong;
    - the template's `tests.match` placeholder silently matched nothing;
    - `install --agent generic` made `check` fail on its own files.
- **Adapt:**
  - `tests.junit` is the report's path, not the runner flag — fix it if it was copied from the
    stack table.
  - In CI, `spry check` now also runs on pushes to `main`. Take the `check` job from
    `templates/ci-github.yml`.
- **Migrate:**
  - A decision's `affects` lists item IDs only. An area name there never matched anything; move
    it into the decision's text.

## CH-4 · Fewer ways to pass by mistake, fewer slow runs

- **Date:** 2026-10-08 · **Version:** 0.4.0
- **Touches:** `tool/spry.py` (`gate`, `changed`, `merge-check`, `pr-body`, test scan),
  `process/{slicing,merging,testing,from-writ,setup}.md`,
  `process/templates/{spry.config.json,ci-github.yml,agents.md,slice.md}`,
  `skills/{slice-open,slice-close,merge}`, `stacks/{generic,python,typescript-node}.md`
- **Why:**
  - People cannot read everything an agent writes, so each place an agent could mark its own work
    as passing is now a check:
    - a comment citing `S-1/AC-1` proved the criterion;
    - the agent chose which controls to falsify, so it could leave out the ones its tests miss;
    - a survivor with any written reason passed `merge-check`;
    - a branch could weaken a criterion and change the code to fit it, with only a warning.
  - Slow runs repeated for nothing. Nothing ran lint before the tests, so a lint error found
    after them meant running them again. A document fixed after the gate re-ran the tests, CI
    ran every test on pushes that changed only documents, and `/spry:merge` ran the full suite
    locally after CI had already run it on main.
  - The agent stopped to ask at every step of a slice. Only three of those are a person's to
    make: the criteria, the merge, and anything hard to undo.
- **Adapt:**
  - `checks.fast`: the project's format, lint and type-check commands, cheapest first (see the
    stack profile). `checks.docs` if documents live outside `spry/` and `*.md`.
  - CI: take the new `templates/ci-github.yml`, which gives fast checks a job of their own and
    skips them and the tests when no code changed.
  - `AGENTS.md` *Commands*: `spry.py gate` replaces the two test lines (see `templates/agents.md`).
- **Migrate:**
  - Tests citing a criterion only in a comment no longer prove it. `spry check` warns for each
    one; move the ID into the test's title string or docstring.
  - Closed slices are not re-checked. An open slice's Falsify table needs a row for every control
    `falsify suggest` lists before it merges.

## CH-5 · The trunk is read, not assumed

- **Date:** 2026-10-09 · **Version:** 0.4.1
- **Touches:** `process/setup.md`
- **Why:** setup left `main_branch` at the template's `main`. A project whose trunk is another
  branch (pulse-v2's is `dev`) would branch slices from the wrong place, and falsify, `merge-check`
  and CI would compare against it.
- **Adapt:** nothing
- **Migrate:** check `main_branch` in `spry/spry.config.json` against the repository's default
  branch.

## CH-6 · A coverage page

- **Date:** 2026-10-09 · **Version:** 0.5.0
- **Touches:** `tool/spry.py` (`coverage`, `index` fills `spry/COVERAGE.md`),
  `process/templates/{coverage,project-readme,roadmap}.md`, `process/setup.md`, `skills/status`
- **Why:** progress showed item by item, in each README and in `status`. Nothing said how much of
  the whole plan was defined, built and proven, or listed the stories whose slices were all closed
  while a criterion still had no proof — the view writ's `COVERAGE.md` gave.
- **Adapt:** nothing
- **Migrate:** add `spry/COVERAGE.md` from `templates/coverage.md`; add the Coverage line to
  `spry/README.md` (*Start here*) and below the milestones block in `spry/plan/README.md`.

## CH-7 · writ's slice summaries are kept

- **Date:** 2026-10-09 · **Version:** 0.6.0
- **Touches:** `process/from-writ.md`, `tool/spry.py` (`check` skips `spry/history/<source>/`;
  `find` lists it last, marked `history`)
- **Why:** adopt left writ's slice summaries only in git history, so each `Built under writ` slice
  said where it came from and nothing about what was built, how, which options were rejected, or
  what was deliberately left out.
- **Adapt:** nothing
- **Migrate:** only for a project adopted from writ: follow `process/from-writ.md` → *Adopted
  before CH-7*.

## CH-8 · writ's requirement details become stories

- **Date:** 2026-10-09 · **Version:** 0.7.0
- **Touches:** `process/from-writ.md`
- **Why:** adopt left requirement detail files out. A detail file says what a person would see —
  job stories, personas, boundary cases, scenarios — and runs to hundreds of lines, so turning only
  its requirement into a story or criterion lost most of it.
- **Adapt:** nothing
- **Migrate:** nothing. It applies only to adopting a writ project that kept detail files.

## CH-9 · After a merge, test only what the PR's checks never saw

- **Date:** 2026-10-09 · **Version:** 0.7.1
- **Touches:** `process/merging.md` (*Merge* steps 7–8), `skills/merge`
- **Why:** after every merge the full suite ran again, on CI or by hand, even when the main branch
  had not moved: the merged code was the code the PR's checks had just passed. On a project whose
  CI runs only on pull requests, that meant a full local gate after each merge.
- **Adapt:** a project with its own after-merge rule (in `AGENTS.md`, say) words it the same way:
  run it only when `spry.py changed --base <PR head>` prints `code=true`.
- **Migrate:** nothing

## CH-10 · A backlog page, and fresh pages on any branch

- **Date:** 2026-10-09 · **Version:** 0.8.0
- **Touches:** `tool/spry.py` (`backlog`, `view`, `hooks`, `index --restore`; `index` fills
  `spry/BACKLOG.md`; `check --base` refuses generated blocks a branch changed),
  `process/templates/{backlog,project-readme,roadmap,ci-github.yml}`, `process/setup.md`,
  `process/slicing.md`, `skills/{slice-open,status}`
- **Why:** choosing the next piece of work meant opening every story, task and bug folder. Nothing
  listed what was being built, what was ready, what still needed slicing or planning, or what was
  blocked and on what — the view writ's `SLICE-QUEUE.md` gave, there kept in order by hand. And the
  generated pages showed the main branch as of CI's last run: running `spry index` locally to see
  more was the way to a conflicting pull request.
- **Adapt:** whether to offer `spry hooks` to each person (one run per clone): after a checkout or a
  pull that changed the plan or a test, they refresh `.spry/view/` and say so.
- **Migrate:** add `spry/BACKLOG.md` from `templates/backlog.md`; add the Backlog line to
  `spry/README.md` (*Start here*) and below the milestones block in `spry/plan/README.md`; in
  `.github/workflows/spry.yml`, add the `git fetch` step before `spry index` in the `index` job, and
  pass `--base` to `check` on pull requests if the workflow does not already.

## CH-11 · The backlog says what each row is part of

- **Date:** 2026-10-09 · **Version:** 0.8.1
- **Touches:** `tool/spry.py` (`backlog`)
- **Why:** a backlog row named only the slice and its story, task or bug. A slice's title rarely
  says which milestone, epic or feature it serves, so choosing one meant opening it.
- **Adapt:** nothing
- **Migrate:** nothing — CI's next `spry index` rewrites the page.

## CH-12 · Fresh eyes on any pull request, posted line by line

- **Date:** 2026-10-09 · **Version:** 0.9.0
- **Touches:** `process/reviewing.md` (new; *Review* moves out of `process/merging.md`),
  `process/interview.md` (*Finishing* offers a review), `process/from-writ.md`, `skills/review`,
  `tool/spry.py` (`review-check`)
- **Why:**
  - `review` knew only slice PRs. A plan PR on a team, or a plan item a solo person committed
    straight to the main branch, had no second reader at all.
  - The review could be run by the session that wrote the work, which reads its own reasons back
    instead of the page.
  - Findings were posted as one block of text: the author had to find each line and retype each
    fix. pulse's `requirement-review` showed the better way — one comment per line, a one-click
    suggested change for wording, each finding verified on its line before anyone sees it.
  - GitHub refuses `REQUEST_CHANGES` on your own PR, which is every PR when solo, and a comment
    anchored outside the diff fails only when it is posted.
- **Adapt:** nothing
- **Migrate:** a project with its own requirement-review skill (pulse) may retire it for `review`.

## CH-13 · The backlog says what each row unblocks and what holds it up

- **Date:** 2026-10-09 · **Version:** 0.10.0
- **Touches:** `tool/spry.py` (`backlog`, `check`), `process/slicing.md` (*Split*),
  `process/conflicts.md`, `skills/slice`
- **Why:**
  - Two ready rows looked alike: nothing said that finishing one would free other work.
  - A blocked row named its blocker but not whether anyone was on it — in progress, ready, or not
    even sliced.
  - `slice` ordered slices "each building on the last" without writing it down, so a slice that
    needed the one before it showed as ready beside it, and two people could pick up both.
  - A `blocked_by` naming a dropped item, or one going in a circle, kept items blocked forever with
    no error.
- **Adapt:** nothing
- **Migrate:** run `spry check`: fix each dropped blocker or circle it names, by removing the entry.
  Slices planned earlier keep their order unwritten; add `blocked_by` where one needs another.

## CH-14 · Fewer re-runs, and the question comes last

- **Date:** 2026-10-09 · **Version:** 0.11.0
- **Touches:** `tool/spry.py` (`gate`, `falsify run`, `falsify --record`, `merge-check`, `check`),
  `process/slicing.md` (*While building*, *Close*), `process/chat.md`, `templates/agents.md`,
  `templates/spry.config.json` (`tests.retry`), `stacks/*`
- **Why:** from the connect pilot, SL-158 to SL-162.
  - The gate ran 3–5 times a slice: affected packages at full concurrency timed out tests the
    change never touched, on a loaded laptop.
  - `merge-check` matched falsify rows by the label `suggest` wrote, so a row renamed in plain words
    blocked the merge and falsify ran again in full — about ten minutes, three times.
  - A control whose criterion about 60 files cite ran all 60 when the one test naming its source
    file would have caught it.
  - A test title with `<token>` inside a generated proof block was flagged as a leftover placeholder.
  - Replies put `ASK` first, ahead of the findings the question turns on.
- **Adapt:** set `tests.retry` — the affected tests with no parallelism (`stacks/<stack>.md`); leave
  it empty to never retry. `tests.retry_when` overrides what counts as a timeout.
- **Migrate:** a project that copied the reply order into its `AGENTS.md` moves `ASK` last. Falsify
  rows recorded earlier have no key and still match by label.

## CH-15 · A merge when CI never ran, and review to merge in one answer

- **Date:** 2026-10-09 · **Version:** 0.12.0
- **Touches:** `process/merging.md` (steps 1, 6, 8), `process/reviewing.md` (§4, §5a),
  `skills/merge`, `skills/review`, `tool/spry.py` (`merge-message --ci-local`)
- **Why:** from the connect pilot, SL-157 to SL-162.
  - A GitHub billing lock kept CI from starting for the whole pilot. All six merges went ahead on a
    rule kept only in the agent's memory, and the merge procedure had no word for a check that never
    ran — only red, which says stop.
  - Four of five reviews took three answers — post, fix, merge — where the person wanted one: "fix
    the two Should items, then merge".
- **Adapt:** nothing
- **Migrate:** a project that kept a "CI is down, merge on a local gate" rule in memory or in
  `AGENTS.md` drops it; step 1 of `merging.md` now holds it.

## CH-16 · Update sees the newest spry; falsify for slices with no guard

- **Date:** 2026-10-09 · **Version:** 0.13.0
- **Touches:** `process/updating.md` (§0), `skills/update`, `process/slicing.md` (*Close*),
  `tool/spry.py` (`falsify suggest`, `merge-check`)
- **Why:** from the connect pilot.
  - `/spry:update` said "nothing new" twice while a newer spry was published: it read the
    changelog of the copy installed. The person updated the marketplace and plugin by hand.
  - `falsify suggest` drafted nothing for SL-161 (a test-only change) and SL-162 (a keyed digest,
    no guard), and `merge-check` blocked on the empty table, so the agent wrote both plans by hand.
  - `suggest` read added lines in Markdown outside `spry/` as source.
- **Adapt:** nothing
- **Migrate:** nothing. This update itself still runs from the old copy: update the plugin by hand
  once (`claude plugin marketplace update`, `claude plugin update spry@<marketplace>`,
  `/reload-plugins`); from then on `/spry:update` does it.

## CH-17 · Status fits a big plan

- **Date:** 2026-10-09 · **Version:** 0.13.1
- **Touches:** `tool/spry.py` (`status`), `skills/status`
- **Why:** on connect, `status` printed 778 lines, every level down to slices; twice the agent cut
  it to milestones and epics by hand. Now, with no level, it prints only the levels that fit in 100
  lines and says how to go deeper — `status <ID>` for one branch, `--level`, or `--all`.
- **Adapt:** nothing
- **Migrate:** nothing

## CH-18 · A GitHub issue per slice, and slice-open that only asks

- **Date:** 2026-10-09 · **Version:** 0.14.0
- **Touches:** `tool/spry.py` (`check`, `issue-body`, `pr-body`, `merge-message`),
  `process/slicing.md` (*Open*, *Close*), `process/setup.md` (§2 b), `process/chat.md` (*Asks*),
  `skills/slice-open`, `skills/slice-close`, `templates/spry.config.json` (`slices`)
- **Why:** connect and pulse-v2 both kept writ's issue per slice: people outside the repository
  follow issues, and a frozen copy of the work order as agreed shows how far the slice moved from
  it. connect also made `slice-open` list slices without recommending one — the plan order knows
  dependencies, not an unsettled design or another team's date — and "propose, then confirm" made
  "no, the other one" feel like a correction.
- **Adapt:**
  - `slices.issue: true` — `slice-open` makes the issue before the branch (`spry.py issue-body`),
    the slice gets `issue:`, `slice-close` comments the close summary, the merge closes it.
  - `slices.pick: ask` — `slice-open` with no ID lists four ready slices and recommends none.
- **Migrate:** a project that already makes issues sets `slices.issue: true` and drops its local
  rule; slices already open keep their `issue:` (a number, no `#`).

## CH-19 · Small fixes from the pilot

- **Date:** 2026-10-09 · **Version:** 0.14.1
- **Touches:** `tool/spry.py` (`link`, `index`, `check`), `process/slicing.md` (*Open*),
  `templates/agents.md`
- **Why:** from the connect pilot, each seen once or twice.
  - SL-162's `pr:` was set with `sed`. `spry.py link SL-n --pr N` (also `--branch`, `--issue`) sets
    them in the front-matter, numbers only.
  - The agent looked for `spry.config.json` at the repository root three times; `AGENTS.md` now
    says where it is.
  - `index` warned about 20 folder indexes with no `summary`, ignored since adoption. A folder's
    index line now shows its count when it has no summary, and says nothing.
  - A bug's slice listing a story's criteria under `covers` got "the parent is not a story", which
    did not say what to do. It now does: `covers: []`, and the test still cites the criterion.
- **Adapt:** nothing
- **Migrate:** add the `Config:` line under `## Project` in `AGENTS.md`.

## CH-20 · IDs and slice claims taken on the main branch

- **Date:** 2026-10-10 · **Version:** 0.15.0
- **Touches:** `tool/spry.py` (`new`, `claim`, `release`, `check --base`, `merge-check`, `backlog`,
  `related`), `process/slicing.md` (*Split*, *Open*, *Close*, *Slices side by side*, *IDs and
  claims*), `process/merging.md` (step 5), `process/planning.md`, `process/recording.md`,
  `process/setup.md` (§2 b, §4), `skills/{slice-open,slice-close,record,bug,task}`,
  `templates/spry.config.json` (`mint`), `templates/ci-github.yml` (comment)
- **Why:** from connect, running sessions side by side on one repository.
  - Two branches each ran `new task` and took the same number. `check` saw it only after the
    merge, when the number was already in branch names, PR titles, `blocked_by`, trailers and test
    names. Most came from bugs, tasks and decisions found mid-slice.
  - `slice-open` set `state: open` on the slice branch, so the main branch's backlog still offered
    the slice, and a second session opened it too.
- **Adapt:** `mint` in config.
  - `main` — the main branch is the counter and the push is the lock. `new` (any type with an ID)
    takes the number in a temporary worktree of `origin/<main>`, pushes `docs(plan): new <ID> …`
    there, retrying when someone pushed first, then merges it into the current branch. `claim
    SL-n` sets `branch:` on the slice there and cuts the branch from that commit; a second claim is
    refused, naming the branch. Offline or refused → it stops and writes nothing. Needs a main
    branch that takes a direct commit of documents.
  - `local` (the default when the key is missing) — as 0.14.1. `check --base origin/<main>` and
    `merge-check --base` now name an ID the branch and the main branch both took, before the merge.
- **Migrate:** add `"mint": "main"` or `"mint": "local"` to `spry/spry.config.json`. A slice already
  being built on a branch needs nothing: `claim` refuses it, because its branch exists. To show it
  as claimed on the main branch too, `spry.py link SL-n --branch <branch>` there and commit.

## CH-21 · writ's documents move into spry, not into history

- **Date:** 2026-10-14 · **Version:** 0.16.0
- **Touches:** `process/from-writ.md` (§1.4 with a `kind` column, §1.7, §1.8 new, §2 steps 3, 4,
  7 and 10, *Adopted before CH-21*), `process/qa.md`, `templates/checks.md` (`### Before you
  start`, several scenarios per AC, `## Runs under writ`)
- **Why:** from connect, before pulse-v2's adopt.
  - Requirement details, QA scenarios and specs are written for people who don't build software,
    and they won't dig through writ's history. `history` had no limit, so connect sent 17 of its 46
    documents there, among them 231 amendments holding the reasoning behind decisions still in
    force.
  - Only each `##` heading of a detail file was checked, so a case could be lost inside a section,
    or summarised away to fit a story's line budget.
  - Manual test scenarios had no row of their own.
  - writ's recorded runs, imported as check-log rows, would prove criteria writ never satisfied, or
    un-prove ones a test proves. They now sit in `## Runs under writ`, which proves nothing.
- **Adapt:** nothing
- **Migrate:** a project adopted from writ before 0.16.0 follows `from-writ.md` *Adopted before
  CH-21*.

## CH-22 · Falsify for a bug's slice

- **Date:** 2026-10-14 · **Version:** 0.16.1
- **Touches:** `tool/spry.py` (test scan, `falsify run`, `falsify suggest`), `process/slicing.md`
  (*Close*)
- **Why:** a bug has no criteria, so its tests name the bug (`B-40 …`). `falsify run` looked up
  `expect` only among `S-n/AC-m` citations and refused the plan ("no test cites B-40"), so every
  control of a bug's slice was probed by hand and accepted at the merge — 7 and 5 controls on two
  slices in a row (issue #1).
- **Adapt:** nothing
- **Migrate:** nothing

## CH-23 · falsify on Windows

- **Date:** 2026-10-14 · **Version:** 0.16.2
- **Touches:** `tool/spry.py` (`shell_quote`, `run_tests`, `stop_group`, `borrow`, `unborrow`,
  `parallel_blocker`, parallel falsify cleanup, `write`)
- **Why:** pulse-v2 has people on Windows (its #475), and none of this had run there.
  - Test paths went to the runner with `\`, so `shlex.quote` wrapped each in single quotes, which
    cmd.exe passes on literally: the runner found no files, and every control failed. Paths now go
    with `/`, double-quoted for cmd when needed; a path with `%` or `"` is refused.
  - Windows has no process groups: a timeout stopped the shell and left its test workers running
    against the mutated file. `taskkill /T /F` now stops the whole tree.
  - Parallel falsify links `node_modules` into each worktree. A symlink needs Developer Mode or an
    administrator there; a junction is now made instead, and when that fails too the refusal says
    what to do.
  - Cleanup now removes every borrowed link itself before `git worktree remove`. Git on Windows
    walks into a junction as if it were a folder, so it would have deleted the main tree's
    dependencies through it.
  - pnpm links a package's dependencies with junctions on Windows, which a copy follows, so a
    worktree would test the unmutated packages. With pnpm, Windows runs falsify one control at a
    time.
  - Files were written with CRLF on Windows; now always LF.
- **Adapt:** nothing
- **Migrate:** nothing

## CH-24 · A writ detail file becomes a feature, and nothing in it is lost

- **Date:** 2026-10-14 · **Version:** 0.17.0
- **Touches:** `process/from-writ.md` (§1.7 rewritten, §1.8, §2 steps 3, 5 and 10)
- **Why:** checked against pulse-v2's 26 detail files (188 jobs) before its pre-work.
  - §1.7 could send content only to a story, so a file holding about seven jobs had no place for
    what it says about the whole requirement: summary, personas, fence, open questions.
  - Personas went to the story's *As*, which holds one role: every *May not*, the permission
    cases, had nowhere to go.
  - Fields tables went to `checks.md` whole, so a default for a blank field was a test step, never
    a criterion.
  - Open questions went to §1.6, and adopt waits until every §1.6 question has an answer: 21 files
    carry some, all for the requirement owner.
  - Reconciliation went to history whole, including 22 `fix`, 8 `change-request` and 4 `open`
    rows: known defects and pending changes vanished, and a criterion with an open defect was
    counted as built.
  - Front matter had no row: a story from a draft nobody reviewed went `ready`.
  - A scenario's *Not testable yet* reached only the mapping file.
  - A fresh-eyes read against two real files found more with no place: the title line, the
    summary's definitions, rules and build state, field limits and refused blanks (a case left as
    only a step), story tags (`[MVP]`, `[P1 — …]`) and waits, items about no single act, answered
    questions read as open, two *Before you start* sections in one `checks.md`, scenarios that
    check several criteria, a bug with no severity, *Related* with no rule, scenario headings
    that collide across files, and conflicts settled by a fix slice's later `holds` row read as
    still open. A feature had no budget rule, so a large
    one could only be summarised.
- **Adapt:** nothing
- **Migrate:** nothing — the only project adopted from writ had no detail files.

## CH-25 · A done page, and a type and a number on every backlog row

- **Date:** 2026-10-14 · **Version:** 0.18.0
- **Touches:** `tool/spry.py` (`done`; `index` and `view` write `spry/DONE.md`; the backlog's *Type*
  column and numbered rows; `check` and `merge-check` on `closed:`),
  `process/templates/{done,backlog,slice,project-readme,roadmap}.md`,
  `process/{setup,slicing,reviewing,from-writ}.md`
- **Why:** the backlog said what was left and the coverage page how much was done, but nothing listed
  what was finished, or when. On the backlog, telling a bug's slice from a story's meant reading to
  the end of *Part of*, and only *Ready to build* numbered its rows, so no other row could be named
  by its place.
  - A slice carries no date, and a merge date read from git differs by clone: CI's index job checks
    out one commit. The date is now `closed:` in the slice, set with `state: closed`.
- **Adapt:** nothing
- **Migrate:** add `spry/DONE.md` from `templates/done.md`; add the Done line to `spry/README.md`
  (*Start here*) and after the Backlog link in `spry/plan/README.md`; add the *Type* sentence to the
  intro in `spry/BACKLOG.md`. Closed slices may get `closed:` from their merge commit
  (`git log -1 --format=%cs --grep "^Slice: SL-<n>$"`); one without it dates its item `—`.

## CH-26 · A criterion that changes under its manual checks

- **Date:** 2026-10-14 · **Version:** 0.19.0
- **Touches:** `tool/spry.py` (`check --base`: `changed_criteria`, `manual_reliance`; `criteria_edits`;
  `git` output read as UTF-8),
  `process/{qa,merging}.md`
- **Why:** `check --base` warned when a criterion's text changed only if a test cited it. When only
  the scenarios in the story's `checks.md` relied on it, a reworded criterion went green: the
  scenarios still checked the old wording, and a `pass` logged before the change kept it proven.
  From issue #2. The warning names each scenario and row still as it was where the branch left the
  main branch; changing a scenario takes it off, and a run logged since then takes them all off.
  Scenarios the branch wrote, and a criterion it struck, ask for no re-read.
  - `check --base`, `merge-check --base` and `pr-body --base` compared criteria with the main
    branch as it is now, so a branch that had not merged main in was blamed for main's rewording.
    All three now compare where the branch left it.
  - On Windows, `git` output was read in the local code page, so a criterion with `·` or `é` read
    as changed under `check --base`; it is now read as UTF-8.
- **Adapt:** nothing
- **Migrate:** nothing

## CH-27 · Scenarios a tester can run cold

- **Date:** 2026-10-14 · **Version:** 0.20.0
- **Touches:** `process/templates/checks.md`, `process/qa.md`, `process/from-writ.md` (§1.8),
  `tool/spry.py` (`check` reads every AC a scenario heading names)
- **Why:** a scenario said what to do and what to see, but not what kind of case it was, where in
  the product it ran, or whether it could run yet; so a story of only happy paths looked done, and a
  case written ahead of its screen looked runnable. *Before you start* said what was needed but not
  who provides it, and a tester found out three scenarios in. Steps named buttons, and went stale
  the week a screen moved. Taken from pulse-v2's writ template, without its *Given* / *Expect*:
  `<what to do> → <what you should see>` already does that job.
  - Each scenario opens with `**Type** … · **Where** … · **Ready** …`. Seven types: happy path,
    negative, permission, another organisation, repeat, at once, boundary.
  - *Before you start* is a *What is needed | Who provides it* table, and a **Not through the
    screen** line when the product cannot set something up.
  - Steps say what to achieve, not what to press; what you should see must be something you could
    be wrong about, and a refusal names what must not happen.
  - The scenario list is read back and cut before any steps are written; scenarios that change
    data use their own, so they run in any order; a story with only happy paths sends its owner a
    question, not a guessed case; a `fail` names its scenario.
  - `check` enforces none of it. It did read only the first AC of `### AC-1, AC-3 · …`; it now
    reads every one.
- **Adapt:** in `process/qa.md` and the template's guide: the types — `another organisation` fits
  a product with tenants; drop it or name your own — and what a tester has, which for a product
  with no screens (a CLI, an API) is not a browser.
- **Migrate:** nothing — scenarios already written stay valid; new ones take the new form, and an
  old one takes it when it is next edited.
