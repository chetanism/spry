---
title: <Security audit | Pre-launch review> — <scope>
summary: <one line for the index: the verdict and the count of findings>
date: <YYYY-MM-DD>
kind: <security | prelaunch>
audience: 6
---
# <title>

<!-- guide: Reader: the team, including product. Audience 6/10 — name the screen, data or rule at risk; paths only in the Where column. Written by /spry:security-audit or /spry:prelaunch. A finding is never fixed here: it becomes a bug or task, and its ID goes in the Action column. -->

## Scope

<!-- guide: what was reviewed — the whole product, a milestone, a slice's diff, an area — and the commit it was reviewed at. -->

## Verdict

<!-- guide: prelaunch: `go`, `go with conditions` (list them) or `no-go` (the blockers). security: one line on the overall state. -->

## Findings

| # | Severity | Finding | Where | Rule | Action |
|---|---|---|---|---|---|

<!-- guide: Severity: blocker · major · minor. Rule: the SEC-n, PERF-n, decision or acceptance criterion it breaks, or — . Action: the B-n / T-n created, or `accepted` with who accepted it. -->

## Checked and fine

<!-- guide: one bullet per area reviewed with nothing found — so the next audit knows it was looked at. -->

## Not checked

<!-- guide: what was out of reach, and why — needs production access, a tool not installed, a person to ask. Delete if none. -->
