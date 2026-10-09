---
title: Updating from spry
summary: How a project takes what spry gained since it was set up — offered entry by entry, adapted, never transplanted.
audience: 7
---
# Updating from spry

Run by `/spry:update`. **Read this file from the plugin, not the project's copy** — the project's
copy is the old one. Replies: `chat.md`.

## 0. The newest spry first

An installed plugin is fixed at the version installed. A newer spry on GitHub is invisible to it — the
changelog read in §2 is the installed one — so "nothing new" means nothing until this step is done.

1. **The copy running:** `version` in `<plugin root>/.claude-plugin/plugin.json`.
2. **Installed by Claude Code** — the plugin root is `…/plugins/cache/<marketplace>/spry/<version>`:
   - `claude plugin marketplace update <marketplace>`, then `claude plugin update spry@<marketplace>`.
   - A newer version installed → **the plugin root for the rest of this procedure is
     `…/plugins/cache/<marketplace>/spry/<new version>`**. Read this file again from there, and every
     plugin file after it. No reload is needed for that.
   - Tell the person to run `/reload-plugins` when the update is done, so the other skills run the
     new copy too.
3. **A git checkout** (`claude --plugin-dir`, or `spry.py install` run from a clone):
   `git -C <checkout> fetch`; behind its upstream → ask to `git pull --ff-only` first.
4. **Cannot tell** (no network, another agent) → say which version runs, and go on.

Say in the reply which version this update reads.

## 1. Where the project stands

- `spry_baseline` and `spry` in `spry/spry.config.json`: the last changelog entry considered, and
  the version vendored.
- `spry/knowledge/process-changes.md`: the project's own process changes — **these are kept**.
- `python3 <plugin>/tool/spry.py vendor --diff --root .`: which files differ from the plugin's.

## 2. What spry gained

Every entry in `<plugin>/CHANGELOG.md` after `spry_baseline`, read from the plugin root §0 settled.
None → say so, offer
`vendor --diff`'s output if anything differs anyway, and stop.

## 3. Check each entry before asking

For each entry, read the files it touches in the plugin and in the project, and decide:

| Finding | Means |
|---|---|
| `clean` | the files differ only by spry's change — `process-changes.md` records no local change to them |
| `local change` | a file it touches was changed by the project (`process-changes.md`) — merge needed |
| `already here` | the project already does this (it may have contributed it) |
| `conflicts` | it contradicts a local change — the person decides which wins |

## 4. Offer, then ask

- One `[Note]` per entry: what it changes for this project, in its own names and paths — not the
  changelog's words.
- One numbered ask per entry not `already here`: `a` take as is · `b` take adapted (say how) ·
  `c` skip (say what is lost). One `(recommended)`.
- The person may answer for a group: "skip everything about CI".

## 5. Port what was chosen

- **Process files:** apply the entry's change to the project's copy; keep every local change.
- **Tool:** replace `spry/tool/spry.py` whole — the tool is never changed locally; a project that
  needs a tool change contributes it (`contributing.md`).
- **Templates:** update the template only. Existing documents change only if the entry's `Migrate`
  says so — then migrate each, and show the list.
- **Adapt, never transplant:** the project's paths, commands, IDs and words.
- Never renumber the project's IDs, rename its folders, or drop a local change without a yes.

## 6. Verify and record

1. `python3 spry/tool/spry.py check` and `index`; fix what they report.
2. Set `spry_baseline` to the last entry considered, and `spry` to the plugin's version.
3. One row per entry in `process-changes.md`: `taken CH-n`, `adapted CH-n` (how), or
   `skipped CH-n` (why).
4. Commit `chore(spry): update to <version>` after asking — through a pull request when a team is
   configured.
