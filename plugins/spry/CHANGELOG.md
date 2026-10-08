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
