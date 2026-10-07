---
id: SL-3
title: CI pipeline
state: closed
owner: Ravi
audience: 8
covers: []
branch: sl-3-ci-pipeline
pr: 7
blocked_by: []
related: []
---
# SL-3 · CI pipeline

## Work order

### Summary

- Every pull request runs affected tests, `spry check` and the type check, in parallel.
- `main` runs all tests and refreshes the progress tables in `spry/`.

### Covers

- [T-1](README.md) — both "Done when" lines

### Plan

- `.github/workflows/pr.yml` — three parallel jobs: `vitest run --changed origin/main`, `spry.py check`, `tsc --noEmit`
- `.github/workflows/main.yml` — `pnpm test:all`, then `spry.py index` and a `[skip ci]` commit
- `.github/workflows/nightly.yml` — `pnpm test:all` at 02:00 UTC
- `vitest.config.ts` — `pool: 'threads'`, JUnit reporter to `reports/junit.xml`

### Tests

- None: proved by the demo.

### Demo

```bash
git switch -c demo-red && echo 'test("red", () => { throw 1 })' > src/red.test.ts
git add -A && git commit -m demo && git push -u origin demo-red
gh pr create --fill --draft && gh pr checks --watch   # vitest job fails
```

### Conflict check

- Checked 2026-09-30 against: T-1, performance, open slices (none)
- No conflicts found.

## Close summary

### Falsify

| Control | Mutation | Expect | Result |
|---|---|---|---|
| — | — | — | not applicable: no code under test |
