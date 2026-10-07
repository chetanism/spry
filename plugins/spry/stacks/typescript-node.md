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
| `tests.all` | `vitest run` (threads by default) | `jest --maxWorkers=50%` |
| `tests.junit` | `--reporter=junit --outputFile=reports/junit.xml` | `jest-junit` |
| falsify runner | `vitest run --bail 1 {files}` | `jest --bail {files}` |

- **Monorepo:** with Turborepo, `turbo run test --filter=...[origin/main]` runs only changed packages
  and their dependents; set `cwd: package` on falsify runners.
- **Integration tests** on a shared database: their own runner entry, matched by
  `**/*.integration.test.ts`, run serially (`--pool=forks --poolOptions.forks.singleFork`), with
  `"parallel": false` so falsify never runs two of them at once.
- **Parallel falsify** shares `node_modules` into each worktree. Generated code outside it (a
  Prisma client in `src/generated`, a build output tests import) goes in `falsify.share`.
- **Deploy exclusion:** add `spry/` to `.dockerignore`; with a bundler, nothing reads `spry/` anyway.
- **CI setup steps:** `actions/setup-node` with the `.nvmrc` version; `pnpm install --frozen-lockfile`
  (or the project's manager) with its cache.
