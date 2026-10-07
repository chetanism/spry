---
title: Contributing to spry
summary: How a project offers spry what it built — judged honestly, stripped of everything private, filed as an issue, never a pull request.
audience: 7
---
# Contributing to spry

Run by `/spry:contribute`. Read this file from the plugin. Replies: `chat.md`.

## 1. Find candidates

The person may name one (`$ARGUMENTS`). Otherwise look at:

- `spry/knowledge/process-changes.md` — rows of kind `local`;
- `python3 <plugin>/tool/spry.py vendor --diff --root .` — files changed or added in the project;
- the project's own skills and commands (e.g. `.claude/skills/`), and `AGENTS.md` rules about *how
  work is done* rather than about this product;
- a stack this project set up that `<plugin>/stacks/` has no profile for.

## 2. Judge each honestly

- **Would another project use it, unchanged in shape?** Product rules, domain words and this team's
  habits are not contributions.
- **Is it already in spry?** Check `<plugin>/CHANGELOG.md` and the plugin's files.
- **Evidence:** how long it has been used here, and what it caught or saved — a slice, a bug, a
  number. No evidence → say so in the issue; it is still worth offering, but labelled untried.
- Offer the candidates as numbered asks: `a` contribute · `b` skip (why) — one `(recommended)`.
  Recommend skipping what is specific to this project.

## 3. Strip everything private

1. Write the issue to `.spry/contribute-<slug>.md` (local, never committed).
2. Rewrite: the product, people, customers and domain words become generic (`the product`,
   `a librarian` → `a user`); IDs become `S-1`, `SL-1`; app paths become `src/…`.
3. `python3 spry/tool/spry.py scrub .spry/contribute-<slug>.md` — lists every product name, team
   name, handle, glossary term, email and URL still in it. Repeat until it lists nothing, or each
   remaining hit is deliberate and you say why.

## 4. The issue

- **Title:** `contribute: <what it does, in a few words>`
- **Sections:** Problem · What we did · The change (the generalised text or diff) · Evidence ·
  Cost and risks · What a project would adapt.

## 5. File it — only on an explicit yes

1. Show the whole issue; ask to file it. Nothing leaves the machine before a yes.
2. `gh issue create --repo <repository> --title "…" --body-file .spry/contribute-<slug>.md`, where
   `<repository>` is `repository` in `<plugin>/.claude-plugin/plugin.json`; if absent, ask.
3. **Never a pull request**, never a push to spry's repository.
4. Add a row to `process-changes.md`: kind `offered`, with the issue link.
