---
title: Checks for S-<n> · <story title>
audience: 4
---
# Checks · S-<n> · <story title>

<!-- guide: Reader: QA. Audience 4/10 — screens, fields, messages; nothing internal. Scenarios are written by /spry:test-scenarios; the log is appended to by whoever runs them. A `pass` row proves its AC when no automated test does. A tester has what a user has — for most products a browser and an account, no terminal and no database (`spry/process/qa.md`). -->

## Scenarios

### Before you start

<!-- guide: optional, first: what has to be true before any scenario below can run, and who makes it true. Then the Not through the screen line: what the product cannot set up, addressed to whoever prepares the environment, never a step for the tester; delete the line when everything can be set up through the product. -->

| What is needed | Who provides it |
|---|---|
| <an account that can do the job, and what it may do> | <who, and from which part of the product> |

**Not through the screen:** <what the product cannot set up, and why>

### <AC-1> · <short name>

<!-- guide: several scenarios may check one AC; each heading starts with it, and `AC-1, AC-3 · …` checks both. Type: one of the types in `spry/process/qa.md`. Where: the part of the product, as a person would say it. Ready: yes, or no and what it waits for. Each step says what to achieve, not what to press, with the data to use; what you should see must be something you could be wrong about. -->

**Type** <happy path> · **Where** <the part of the product> · **Ready** <yes>

1. <what to achieve> → <what you should see>

## Check log

<!-- guide: append only; never edit a past row. `build` is the version, commit or deploy that was tested. A `fail` names the scenario in Notes. -->

| Date | AC | Build | By | Result | Notes |
|---|---|---|---|---|---|
