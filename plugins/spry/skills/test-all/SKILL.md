---
name: test-all
description: Run the whole test suite on purpose, timing each part. Report only. Use only when a person asks to run all the tests.
argument-hint: "[part name, optional]"
---

# spry — test-all

- **Procedure:** `spry/process/testing.md` → *Full suite* — print only it: `python3 spry/tool/spry.py proc testing "Full suite"`.
  Read `chat.md` beside it.
- **Parts:** `tests.parts` in `spry/spry.config.json`, or `tests.all` alone. `$ARGUMENTS`, if
  given, names one part.
- **Never** edit code or tests, or skip, retry or quarantine a test to get green.
- **Stop only a stack this run started** — and always stop it, even after a failure.
