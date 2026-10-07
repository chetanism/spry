---
title: Changing the process
summary: How this project changes spry's process for itself — every file the change touches, in one change, recorded so updates keep it.
audience: 7
---
# Changing the process

Run by `process-change`. Tone: audience 7. The process is the project's to change; this makes the
change complete and keeps it through `/spry:update`.

1. **Say the change in one sentence**, and the problem it answers. Ask if either is unclear.
2. **Find every file it touches:** `spry/process/*.md`, `spry/process/templates/*`,
   `spry/spry.config.json`, `AGENTS.md`, the CI workflow, and the skills when the project has its
   own copies. Search for the words the change alters (`grep -rn`), not only the obvious file.
3. **Never edit `spry/tool/spry.py`.** It is replaced whole on update. A change that needs the tool →
   `/spry:contribute` it, and work around it in the process text meanwhile.
4. **Show the list**: one line per file and what changes in it. Apply only on a yes.
5. **Apply all of it** in one change; documents already written to an older template change only
   if the person asks — list them.
6. **Record** a row in `spry/knowledge/process-changes.md`: date, the change, kind `local`, the files,
   why. This row is what lets `/spry:update` keep the change.
7. `spry.py check`; commit `chore(process): <the change>` — through a pull request when a team is
   configured.
8. **Offer `/spry:contribute`** in one line when the change would help other projects too.
