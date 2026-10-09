---
title: TypeScript / Node
summary: Test commands, parallelism, falsify runners and deploy exclusion for a TypeScript or Node project.
audience: 8
---
# TypeScript / Node

| Config key | Vitest | Jest |
|---|---|---|
| `tests.match` | `["**/*.test.ts", "**/*.test.tsx"]` | same |
| `tests.affected` | `vitest run --changed origin/main` | `jest --changedSince=origin/main` |
| `tests.retry` | `vitest run --changed origin/main --no-file-parallelism` | `jest --changedSince=origin/main --runInBand` |
| `tests.all` | `vitest run` (threads by default) | `jest --maxWorkers=50%` |
| `tests.junit` | `reports/junit.xml` — the runner writes it with `--reporter=junit --outputFile=reports/junit.xml` | the file `jest-junit` writes (`JEST_JUNIT_OUTPUT_FILE`) |
| falsify runner | `vitest run --bail 1 {files}` | `jest --bail {files}` |
| `checks.fast` | format `prettier --check .` · lint `eslint . --cache` · types `tsc --noEmit` | same |

- **Fast checks** run before any test, in `spry.py gate` and in CI. Use the project's own tools
  if it has others (Biome, oxlint, oxfmt). In a Turborepo, filter them like the tests:
  `turbo run lint typecheck --filter=...[origin/main]`.
- **Test names** carry the citation in the title string: `test("S-1/AC-2 refuses a fifth book", …)`.
  A citation in a comment proves nothing.

- **Monorepo:** with Turborepo, `turbo run test --filter=...[origin/main]` runs only changed packages
  and their dependents; set `cwd: package` on falsify runners. `tests.retry` is the same command with
  `--concurrency=1`: Turbo's cache skips the packages that passed, so only the timed-out one re-runs.
- **Integration tests** on a shared database: their own runner entry, matched by
  `**/*.integration.test.ts`, run serially (`--pool=forks --poolOptions.forks.singleFork`), with
  `"parallel": false` so falsify never runs two of them at once.
- **Parallel falsify** shares `node_modules` into each worktree. Generated code outside it (a
  Prisma client in `src/generated`, a build output tests import) goes in `falsify.share`.
- **Deploy exclusion:** add `spry/` to `.dockerignore`; with a bundler, nothing reads `spry/` anyway.
- **CI setup steps:** `actions/setup-node` with the `.nvmrc` version; `pnpm install --frozen-lockfile`
  (or the project's manager) with its cache.
