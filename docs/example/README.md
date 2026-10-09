# Worked example — Shelf

An invented product, taken from roadmap to slice, to show what a spry project looks like.
Shelf is a lending desk for a small community library. Three people: Asha (product), Ravi
(developer), Meera (QA).

**Start where a team member would:** [`spry/README.md`](spry/README.md), then click down.

## What it shows

| Where | What to look at |
|---|---|
| [Roadmap](spry/plan/README.md) → [M-1](spry/plan/M-1-members-borrow-books/README.md) → [E-1](spry/plan/M-1-members-borrow-books/E-1-lending/README.md) → [F-1](spry/plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/README.md) | The hierarchy as folders; each page written for a non-technical reader |
| [S-1 Lend a book](spry/plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/S-1-lend-a-book/README.md) | A story **reopened by a bug**: its slice is done, but QA's latest check of AC-2 failed (B-1), so it shows "not proven" |
| [S-1 checks](spry/plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/S-1-lend-a-book/checks.md) | QA's scenarios and check log; the failed row that became B-1 |
| [SL-1 Record a loan](spry/plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/S-1-lend-a-book/SL-1-record-a-loan.md) | A **closed** slice: summary, plan, falsify with one survivor fixed |
| [SL-2 Refuse a loan over the limit](spry/plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/S-2-loan-limit/SL-2-refuse-over-limit.md) | An **open** slice: work order only, conflict check against another slice and a bug |
| [B-1](spry/plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/bugs/B-1-due-date-a-day-early/README.md) · [T-1](spry/plan/M-1-members-borrow-books/tasks/T-1-set-up-ci/README.md) | A bug with a **planned** slice, and a task — attached, but not counted toward progress |
| [F-2 Return a book](spry/plan/M-1-members-borrow-books/E-1-lending/F-2-return-a-book/README.md) | A **draft** feature: no conflict check yet, an open question |
| [Backlog](spry/BACKLOG.md) | What to pick up next, derived from the plan: SL-2 in progress, SL-4 ready to build, F-2 waiting on product |
| [Coverage](spry/COVERAGE.md) | The whole plan at a glance: done vs defined, criteria proven, and S-1's AC-2 listed as built but not proven |
| [Glossary](spry/knowledge/glossary.md) | One term per concept, with the words not to use |
| [Knowledge](spry/knowledge/) | Index → item: decisions, conventions, an external service's behaviour |

## Written by people vs generated

- **Written** (by a person, or an agent in an interview): everything outside the marker blocks.
- **Generated** by `spry index` on `main`: everything between `<!-- spry:… -->` and
  `<!-- /spry:… -->` — progress tables, proof tables, index lines.

## Try the tool on it

```bash
python3 plugins/spry/tool/spry.py --root docs/example check
python3 plugins/spry/tool/spry.py --root docs/example status
python3 plugins/spry/tool/spry.py --root docs/example coverage
python3 plugins/spry/tool/spry.py --root docs/example backlog
python3 plugins/spry/tool/spry.py --root docs/example related \
  docs/example/spry/plan/M-1-members-borrow-books/E-1-lending/F-1-lend-at-the-desk/S-2-loan-limit/SL-2-refuse-over-limit.md
```

`status` prints:

```
M-1 Members can borrow books                                  0 of 1 epics done · 1 open bug
  E-1 Lending                                                 0 of 2 features done · 1 open bug
    F-1 Lend at the desk                                      0 of 2 stories done · 1 open bug
      S-1 Lend a book                                         not proven · 1 of 1 slices · 2 of 3 criteria proven
        slice SL-1 Record a loan                              done · PR #9
      S-2 Loan limit                                          in progress · 0 of 1 slices · 0 of 2 criteria proven
        slice SL-2 Refuse a loan over the limit               open · PR #14
      bug B-1 Due date a day early on evening receipts        0 of 1 slices done
        slice SL-4 Due date in the library's time zone        planned
    F-2 Return a book                                         no stories yet
  task T-1 Set up CI                                          done
    slice SL-3 CI pipeline                                    done · PR #7
```
