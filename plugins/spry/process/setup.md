---
title: Setting up
summary: What init and adopt ask, in what order, and every file they write.
audience: 7
---
# Setting up

Run by `init` (new project) and `adopt` (existing code). Interview rules: `interview.md`. Tone:
audience 3 until the stack section, which is for a developer — skip it if none is present and
record it under Open questions.

## 0. Bring spry in

```
python3 <plugin>/tool/spry.py vendor --root .
```

Copies `process/` and the tool into `spry/process/` and `spry/tool/`. From then on, every agent
uses `python3 spry/tool/spry.py`.

## 1. The starting point

Ask for the high-level description: what is being built, for whom, why now. A paragraph or a pasted
document both work. Everything after is drafted from it, so read it twice.

## 2. Interview — in this order

| # | Topic | Writes |
|---|---|---|
| a | Product and the people who use it | roadmap `Where we are going`; glossary rows for each role |
| b | Team — names, GitHub handles, roles (product, developer, qa, …), who reviews what | `team` in config; empty = solo |
| c | Plan shape — levels (offer dropping Epic for small projects); ID prefixes (offer the defaults, shown as `S-12 · Book a walk-in`) | `levels`, `ids` in config |
| d | Roadmap — the milestones in order; the next 1–3 in a sentence each | `spry.py new milestone` for each near one (title + `Why` only, `draft`); the rest as `Later` lines |
| e | Constraints — dates, budget, hosting, regulation, systems that must be used | `knowledge/constraints.md` |
| f | Security — who may see what, personal data, sign-in, audit | `knowledge/security.md`, rules `SEC-n` |
| g | Performance — load, response times, devices, data volumes | `knowledge/performance.md`, rules `PERF-n` |
| h | External services — each one the product depends on | `knowledge/external/<service>/INDEX.md` each |
| i | Stack and tests (developer) — language, framework, test runner, CI host | `tests` and `falsify` in config, from `stacks/<stack>.md` |
| j | Words — every term used so far, its meaning, its synonyms | `knowledge/glossary.md` |

## 3. Write the rest

| File | From |
|---|---|
| `spry/spry.config.json` | `templates/spry.config.json` + answers |
| `spry/README.md` | `templates/project-readme.md` |
| `spry/plan/README.md` | `templates/roadmap.md` |
| `spry/knowledge/{conventions,decisions}/INDEX.md` | `templates/index.md` |
| `spry/knowledge/process-changes.md` | `templates/process-changes.md` |
| `AGENTS.md` | `templates/agents.md` — within 150 lines; the admission test stays at the top |
| `CLAUDE.md` | the single line `@AGENTS.md` |
| `.gitignore` | add `.spry/` |
| deploy exclusion | `spry/` in `.dockerignore`, or the stack's build ignore — `stacks/<stack>.md` |
| `.github/workflows/spry.yml` | `templates/ci-github.yml`, commands filled in |
| `.github/CODEOWNERS` | one line per `team.review` glob, owners by role; skip when solo |

## 4. Finish

1. `python3 spry/tool/spry.py check` and `python3 spry/tool/spry.py index`; fix what they report.
2. Show what was written, at the person's tone, grouped: plan · knowledge · process · CI.
3. Commit `chore(spry): set up spry`, after asking.
4. `NEXT`: `/spry:milestone M-1` to define the first milestone.

## Adopt — what changes

`adopt` puts spry around code that already exists **without blocking anyone**: `spry check` only
reads `spry/` and test names, so no existing file can fail it.

1. **Survey before asking.** Read and record in `spry/knowledge/codebase.md` (index → item when over
   budget):
   - stack, package manager, test runner, the commands that run tests, and how long a full run takes;
   - the main areas of the code, one line each — what exists, by area;
   - existing documents (README, `docs/`, decision records, `CLAUDE.md` / `AGENTS.md`);
   - external services, from the dependency manifests and configuration;
   - domain words that recur in type and table names — glossary candidates.
2. **Interview as in §2,** but every ask offers the surveyed answer for confirmation. Topic d starts
   from the *next* work, not from what exists.
3. **Existing instructions:** merge an existing `CLAUDE.md` / `AGENTS.md` into the new `AGENTS.md`
   under the admission test; what does not pass moves to `knowledge/conventions/`, never deleted.
4. **Existing decision records:** offer to move each to `knowledge/decisions/` as `D-n`, keeping its text.
5. **Existing CI:** add the spry jobs beside what is there; never replace a workflow.
6. **Existing tests:** untouched. Only new tests cite criteria.
