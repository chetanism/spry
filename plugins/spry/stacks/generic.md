---
title: Any other stack
summary: What to find out when no stack profile fits.
audience: 8
---
# Any other stack

Ask the developer for, and record in config:

- `tests.match` — globs that find test files;
- `tests.affected` — a command that runs only tests affected by the change; if the runner has none,
  run the test files beside the changed source files, and say so in `AGENTS.md`;
- `tests.retry` — the affected tests again with no parallelism, run once by `gate` when the first run
  failed on a timeout (`tests.retry_when`, default `timed out|timeout|ETIMEDOUT`); empty to never retry;
- `tests.all` — every test, in parallel where the runner allows;
- `checks.fast` — format, lint and type checks, cheapest first; they run before any test;
- `checks.docs` — globs for files whose change never needs a test run (default `spry/**`, `**/*.md`);
- `tests.junit` — where a JUnit XML report is written, if the runner can;
- `tests.parts` — when the suite has parts that run differently (unit, integration, end to end):
  each part's command, and whether it needs local services; leave it out when `tests.all` is all;
- `stack` — commands that check, start and stop the local services (database, queues), if any;
- `explore` — how to run a second, isolated instance for `/spry:explore`; may be left `<…>`
  until the first exploratory run, which stops and asks;
- falsify runner — runs a list of test files (`{files}`), stopping at the first failure;
- deploy exclusion — how `spry/` is kept out of the build.

A criterion is cited by putting `S-1/AC-1` in the string that names the test — its title, or a
docstring. A citation in a comment or in code proves nothing.
