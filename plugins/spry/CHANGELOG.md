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
