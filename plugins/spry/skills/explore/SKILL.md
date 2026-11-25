---
name: explore
description: Exploratory manual testing: a seeded, replayable walk over a real instance. Report only. Use when asked to manually test or smoke-test.
argument-hint: "[area] [sanity | regular | deep | adversarial] [seed to replay]"
---

# spry — explore

- **Procedure:** `spry/process/testing.md` → *Explore* — print only it: `python3 spry/tool/spry.py proc testing Explore`. Read
  `chat.md` beside it.
- **Instance:** `explore` in `spry/spry.config.json`. Any value still `<…>` → stop and fill it with
  the developer first; never fall back to the development instance.
- **Asks:** area, depth and seed — take any already in `$ARGUMENTS`, ask the rest in one message.
- **Report only:** findings go to the reply and `.spry/explore/<seed>/`; a defect becomes a bug
  only when the person says yes.
