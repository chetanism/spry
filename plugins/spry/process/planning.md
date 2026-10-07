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

The command picks the next ID, the folder and the template. Interview into that file (`interview.md`).
**An existing `draft`** named in the arguments — for example a milestone `init` created — is continued
instead: read it, then interview only for its empty sections.

## 4. Define this level only

| Level | Settles | Leaves for later |
|---|---|---|
| milestone | why, done-when a person can check, in/out of scope, constraints | epics |
| epic | why, who it is for, done-when, in/out of scope | features |
| feature | summary, who, how it works step by step, numbered rules, out of scope | stories |
| story | one story per file; criteria as Given / When / Then | slices |

- **Stories:** one run may create several stories under the same feature — one `new story` each.
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
