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
- `tests.all` — every test, in parallel where the runner allows;
- `tests.junit` — where a JUnit XML report is written, if the runner can;
- falsify runner — runs a list of test files (`{files}`), stopping at the first failure;
- deploy exclusion — how `spry/` is kept out of the build.

A criterion is cited by putting `S-1/AC-1` anywhere on the line that names the test.
