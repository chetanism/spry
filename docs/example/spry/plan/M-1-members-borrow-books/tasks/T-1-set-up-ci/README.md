---
id: T-1
title: Set up CI
state: ready
owner: Ravi
audience: 7
blocked_by: []
related: []
---
# T-1 · Set up CI

## Why

- No slice can prove its acceptance criteria until tests run on every pull request.

## What changes

- A pull request runs affected tests, `spry check` and the type check, in parallel.
- `main` runs every test, then `spry index`; a nightly job runs every test again.

## Done when

- A pull request with a failing test cannot show green.
- Affected tests on a typical pull request finish in under 3 minutes.

## Conflict check

- Checked 2026-09-30 against: M-1, performance, open slices (none)
- No conflicts found.

## Slices

<!-- spry:children -->
| Slice | State |
|---|---|
| [SL-3 CI pipeline](SL-3-ci-pipeline.md) | done · PR #7 |
<!-- /spry:children -->
