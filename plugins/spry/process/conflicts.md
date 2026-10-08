---
title: Conflict check
summary: How a milestone, epic, feature, story or slice is checked against everything it could clash with, and how the result is recorded.
audience: 7
---
# Conflict check

Run by `milestone`, `epic`, `feature`, `story` and `slice-open`, on the draft, before it goes
`ready` (plan items) or `open` (slices). Re-run after any change to the draft's scope.

## 1. Gather

```
python3 spry/tool/spry.py related <path-to-draft>
```

Lists candidates; read every one:

- the parent and its parent;
- siblings under the same parent;
- items sharing a glossary term with the draft;
- full-text hits on the draft's key phrases, across all of `spry/plan/`;
- the knowledge files listed in `always_check` in `spry.config.json`;
- decisions whose `affects` names the draft or one of its parents;
- **slices only:** every `open` slice, and the files its plan lists.

## 2. Classify

| Kind | Means | Resolve by |
|---|---|---|
| `Duplicate` | another item already says this | ask: merge, drop, or tell them apart |
| `Overlap` | part of this is already covered elsewhere | narrow one of them; say which in both |
| `Contradiction` | this says the opposite of an item, decision or rule | ask: which one wins |
| `Dependency` | this needs another item first | add it to `blocked_by` |
| `Scope` | this is outside its parent's in/out scope | ask: move it, or widen the parent |
| `Term` | a word clashes with the glossary | use the glossary term, or add a row |
| `Collision` | slice: touches the same files as an open slice | order them, or merge them |

## 3. Record

In the document's `Conflict check` section (`##` in plan items, `###` under the slice's `Work order`):

```
- Checked 2026-10-08 against: F-1, S-1, glossary, security, D-1
- Overlap: S-1 Lend a book also refused over-limit loans → S-1 narrowed to the allowed case
- Dependency: needs T-1 Set up CI → added to blocked_by
- Contradiction: D-1 says due date is stored; draft computed it → open
```

- First line: `Checked <date> against: <what>`.
- One line per finding: `<Kind>: <item or file> <what> → <resolution>`.
- `→ open` for anything not yet resolved.
- No findings → `- No conflicts found.` under the first line.
- `spry check` refuses `ready` / `open` without a `Checked` line, or with any `→ open`.
