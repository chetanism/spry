---
name: status
description: Show how far the project has got — done versus total at every level, open slices and open bugs — explained at the reader's tone. Use when someone asks where things stand.
argument-hint: "[ID, or a level such as feature]"
---

# spry — status

1. Run `python3 spry/tool/spry.py status` (add `--level <level>` when `$ARGUMENTS` is a level).
   With an ID, show only that item's branch of the tree.
2. Reply per `spry/process/chat.md`, at the tone in `.spry/tone`, else 3.
   - **Tone 1–4:** a few `[Note]` bullets per milestone in plain words — what is done, what is being
     built, what is stuck and why. Titles, not IDs alone. No tree.
   - **Tone 5–10:** the tree as printed, then `[Note]` bullets for what stands out: stories not
     proven, open bugs, slices open longer than the rest.
3. Never invent progress: everything comes from the tool's output.
