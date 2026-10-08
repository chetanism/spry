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
