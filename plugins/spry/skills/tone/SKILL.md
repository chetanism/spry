---
name: tone
description: Set how technical the agent's replies are for you, from 1 to 10, or reset to each document's default.
argument-hint: "<1-10 | reset>"
---

# spry — tone

- `$ARGUMENTS` is a number 1–10 → write it, alone, to `.spry/tone` (create `.spry/`; it is
  gitignored). Reply with one `[Changed]` bullet, written at the new tone.
- `reset` → delete `.spry/tone`. Tone then follows each document's `audience`.
- Empty → say the current tone and where it comes from, and the 1–10 scale in one line each for 2, 5, 8.
- The setting is this person's only; never commit it.
