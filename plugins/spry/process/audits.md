---
title: Audits
summary: How a security audit and a pre-launch review are run, written up, and turned into bugs and tasks — never fixed in passing.
audience: 7
---
# Audits

Run by `security-audit` and `prelaunch`. Tone: audience 8 while working, 6 in the report. Both
**report and record; neither fixes.** A finding becomes a bug or task the person approves.

## Start

1. Ask the scope: the whole product, a milestone, an area, or a branch's diff. Record the commit.
2. `spry.py new audit --title "Security audit — <scope>"` (or `Pre-launch review — <scope>`)
   creates the report in `spry/knowledge/audits/`.
3. Read `spry/knowledge/security.md`, `performance.md`, `constraints.md`, the decisions index, and
   the previous report of the same kind — re-check its open findings first.

## Security audit

For each area, look at the code, not only the documents:

| Area | Look for |
|---|---|
| Access | every route, query and screen that returns data: who may call it, and is that checked server-side |
| Sign-in and sessions | expiry, reset flows, rate limits, what a stolen session reaches |
| Input | validation at the edge; injection through queries, shell, templates, file paths |
| Personal data | what is stored, logged, sent to third parties; the `SEC-n` rules |
| Secrets | in code, history, logs, client bundles; how they reach production |
| Dependencies | the stack's audit command (`npm audit`, `pip-audit`, …); unmaintained packages |
| External services | what we send them; what we trust from them (`knowledge/external/`) |

Every `SEC-n` rule gets a line: held (where it is enforced) or broken (a finding).

## Pre-launch review

A go / no-go before the first release, or a major one:

| Check | From |
|---|---|
| Every story of the milestone done; none `not proven` | `spry.py status` |
| No open `blocker` bug; every open `major` accepted by name | the plan's bugs |
| A security audit of this scope within the last milestone, its findings closed or accepted | `knowledge/audits/` |
| Every rule whose *How it is checked* says manual has been checked on this build | `security.md`, `performance.md` |
| Configuration and secrets set for production; nothing development-only enabled | the deploy setup |
| Data: migrations run forward cleanly; a backup exists and a restore has been tried | the deploy setup |
| Someone is told when it fails: logs, alerts, error reporting reach a person | the deploy setup |
| `spry/` and other non-product files are not in the build | the build output |
| The constraints still hold: dates, legal, privacy notices | `constraints.md` |

The verdict is `go`, `go with conditions` (listed), or `no-go` (the blockers). **Never deploy.**

## Finish

1. Fill the report: findings with severity, where, the rule broken; `Checked and fine`; `Not checked`.
2. Ask, as numbered asks, which findings become bugs (`spry.py new bug`) or tasks (`new task`) and
   which are accepted, and by whom. Put each ID or `accepted — <name>` in the Action column.
3. `spry.py check`; commit `docs(audit): <title>`.
