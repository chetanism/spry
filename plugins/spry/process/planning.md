---
title: Planning
summary: The one procedure behind milestone, epic, feature and story — define one level, never the level below.
audience: 7
---
# Planning

Run by `milestone`, `epic`, `feature` and `story`. Each skill names its level; everything else is
here. Interview rules: `interview.md`. Tone: the template's `audience` (2–3) — the person is
usually not technical.

## 1. Find the parent

- `milestone` has none. Every other level needs one: the argument, or ask — list the candidates from
  `python3 spry/tool/spry.py status --level <parent level>` with their titles.
- A parent in `draft` → say so, and ask whether to continue anyway (its scope may still move).
- Levels come from `levels` in `spry/spry.config.json`; a project without epics puts features
  straight under milestones.

## 2. Read before asking

- The parent and its parents, and every sibling at this level (`spry.py related` on the parent's
  README lists them).
- `spry/knowledge/glossary.md`, and the knowledge files in `always_check`.
- For a story: the feature's `Rules` — criteria cite them (`F-1/R-2`), never restate them.

## 3. Create the draft

```
python3 spry/tool/spry.py new <level> --parent <parent ID> --title "<working title>" --owner "<name>"
```

The command picks the next ID, the folder and the template. With `mint: main` the ID is taken on
the main branch and pushed at once (`slicing.md` → *IDs and claims*), so the parent must be there. Interview into that file (`interview.md`).

**Several at once** — the stories of a feature, or a list of titles the person gave in one go —
take one call, not one per item: each `new` with `mint: main` is a fetch and a push.

```
python3 spry/tool/spry.py new story --parent F-3 --title "Renew a loan" --title "Refuse a renewal"
python3 spry/tool/spry.py new --batch items.json   # mixed types and parents; `-` reads stdin
```

`items.json` is a list of `{"type", "title", "parent", "owner", "key"}`; `parent` names an item in
the plan or the `key` of an earlier entry — a feature and its first stories in one call. IDs are
numbered in order, one commit holds them all, and if one fails `check` none is written.
**An existing `draft`** named in the arguments — for example a milestone `init` created — is continued
instead: read it, then interview only for its empty sections.

## 4. Define this level only

| Level | Settles | Leaves for later |
|---|---|---|
| milestone | why, done-when a person can check, in/out of scope, constraints | epics |
| epic | why, who it is for, done-when, in/out of scope | features |
| feature | summary, who, how it works step by step, numbered rules, out of scope | stories |
| story | one story per file; criteria as Given / When / Then | slices |

- **Stories:** one run may create several stories under the same feature — agree the titles, then
  one `new story` with a `--title` each (§3).
- **Acceptance criteria** — each one:
  - observable by a person using the product, at audience 3;
  - one behaviour; "and" joining two outcomes means two criteria;
  - specific enough to become a test name and a manual check;
  - numbered `AC-1…`, never renumbered; dropping one strikes it through (`~~AC-2~~`).
- **A story over 6 criteria** → offer to split it before going on.

## 5. Finish

`interview.md` → *Finishing*: conflict check, summary, `ready`, `spry check`, commit. Then offer the
next step in one line: the level below (`/spry:epic`, `/spry:feature`, `/spry:story`), or for a
ready story, `/spry:slice`.

## Bugs and tasks

Run by `bug` and `task`. Same interview rules; neither counts toward its parent's progress.

| | Bug | Task |
|---|---|---|
| Parent | the feature or story it breaks (`bugs/`) | the milestone or epic it serves (`tasks/`) |
| Tone | the template's: 4 | the template's: 7 |
| Settles | what happens, what should, steps, where, impact, severity, `breaks` | why, what changes, done-when, risks |
| Before `ready` | reproduced by the reporter or the agent; a conflict check for duplicates among open bugs | a conflict check |

- **A bug that breaks an acceptance criterion** names it in `breaks: [S-1/AC-2]`. If QA saw it on a
  build, add a `fail` row to the story's `checks.md` — that is what un-proves the criterion.
- **Severity:** `blocker` (stops a release), `major` (a criterion or rule fails), `minor` (anything else).
- **Finish** as `interview.md` → *Finishing*, then offer `/spry:slice <ID>`.

## From a GitHub issue

Anyone — people outside the team too — may ask for work in a GitHub issue (`templates/issue-forms/`),
and anyone may discuss it there. Once it is agreed, a planning skill takes it: `/spry:feature #42`,
`/spry:story #42`, `/spry:bug #42`, `/spry:task #42`, `/spry:epic #42` or `/spry:milestone #42`.

1. **Read it all:** `gh issue view <n> --comments`. The issue and its discussion are the starting
   draft: a question they settled is not asked again; one they left open is.
2. **Not agreed yet** — questions unanswered, people still disagreeing → say what is open, offer to
   ask it on the issue (`gh issue comment`, audience 2–3), and stop.
3. **What it becomes:** usually one item. A large request may become an epic and its features, and a
   mixed one a bug and a story — each names the issue. Part of it may wait: then say on the issue,
   in plain words, what was taken and what stays open.
4. **Nothing private comes into the plan.** Read the project's security rules (`always_check`).
   People's names, contact details, health, money or account records, and screenshots of them are
   never copied — the plan describes the case instead ("a patient with two bookings on one day").
   Passwords, codes and tokens never. Git keeps whatever is committed, for good.
5. **Create, then link:** the level's procedure as usual (§1–§5, or *Bugs and tasks*), then
   `spry.py link <ID> --issue <n>` on each item the issue asked for — it adds `<n>` to `issues:`.
6. **After the commit:** `spry.py issues --sync` — the issue gets `spry:accepted` (or `spry:ready`)
   and a comment naming each item, with a link.
7. **From then on the plan is the record.** A change asked for on the issue is a change to the item,
   agreed with its owner through the planning skill — never copied from the issue on its own.

**Stages.** One `spry:` label at a time, and a plain comment when it changes. All derived (DESIGN.md
§6), never typed:

| Label | When |
|---|---|
| `spry:accepted` | an item names the issue; still `draft` |
| `spry:ready` | every item it names is `ready` |
| `spry:in-progress` | a slice under any of them is claimed, open or closed — or some are done, not all |
| `spry:done` | every item it names is done; dropped ones do not count |
| `spry:declined` | every item it names was dropped |

- **spry never closes an issue.** QA, or whoever asked, closes it after testing. A closed issue is
  left alone; reopening it hands it back to spry.
- **A problem found in testing** → `/spry:bug #42`: a new bug names the same issue, which goes back
  to `spry:in-progress` until the bug is done.
- **When it runs:** `issues --sync` is safe to run any time — it changes only what is out of step.
  CI runs it on the main branch after `index` (`templates/ci-github.yml`), `/spry:merge` after each
  merge (`merging.md` step 8), and this procedure after linking. A project with no CI on push runs it
  on a schedule instead, so a merge made outside `/spry:merge` still reaches its issue.
  `spry.py issues` alone shows each issue's stage and which are out of step.
- **Deploys:** spry knows when work is merged, not when it is deployed. A project whose deploy knows
  what it shipped may tell the issues itself — `spry.py issues --json` gives each issue's items and
  stage — recorded as a local process change (`changing.md`).
