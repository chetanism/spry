---
name: test-all
description: Run the whole test suite on purpose — spry check, each test part in order, the stack brought up and down around the parts that need it — timing each part and naming failures, slow tests and flaky ones. Report only; never fixes, skips or retries. Use before closing a slice that touched shared code, after a dependency or configuration change, or when asked to run all the tests.
argument-hint: "[part name, optional]"
---

# spry — test-all

- **Procedure:** `spry/process/testing.md` → *Full suite*. Read `chat.md` beside it.
- **Parts:** `tests.parts` in `spry/spry.config.json`, or `tests.all` alone. `$ARGUMENTS`, if
  given, names one part.
- **Never** edit code or tests, or skip, retry or quarantine a test to get green.
- **Stop only a stack this run started** — and always stop it, even after a failure.
