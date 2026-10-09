---
name: status
description: Show how far the project has got — done versus total at every level, open slices and open bugs — and what to pick up next, explained at the reader's tone. Use when someone asks where things stand or what to work on next.
argument-hint: "[ID, or a level such as feature]"
---

# spry — status

1. Run `python3 spry/tool/spry.py status`, with `$ARGUMENTS` as given: an ID shows only that
   item's branch, a level is `--level <level>`. A big plan is printed only as deep as fits; show it
   as printed, and offer one branch (`status <ID>`) for whatever the person asks about next — never
   `--all` unless they ask for everything.
2. Reply per `spry/process/chat.md`, at the tone in `.spry/tone`, else 5 (`chat.md`).
   - **Tone 1–4:** a few `[Note]` bullets per milestone in plain words — what is done, what is being
     built, what is stuck and why. Titles, not IDs alone. No tree.
   - **Tone 5–10:** the tree as printed, then `[Note]` bullets for what stands out: stories not
     proven, open bugs, slices open longer than the rest.
3. When the person asks how much is done overall, or what is built but not proven, run
   `python3 spry/tool/spry.py coverage` and answer from it.
4. When the person asks what to work on next, what is blocked, or what still needs planning, run
   `python3 spry/tool/spry.py backlog` and answer from it — *Ready to build* for developers,
   *Needs planning* for product.
5. Never invent progress: everything comes from the tool's output.
