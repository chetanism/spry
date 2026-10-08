---
name: explore
description: Exploratory manual testing — a seeded, replayable random walk over a real, isolated instance, combining actions in orders nobody wrote down, each step predicted from the area's acceptance criteria before it runs, ending in a classified report of defects and gaps. Report only; never edits the repository. Use when asked to manually test, explore, poke at, smoke-test or sanity-check the product beyond what the tests assert.
argument-hint: "[area] [sanity | regular | deep | adversarial] [seed to replay]"
---

# spry — explore

- **Procedure:** `spry/process/testing.md` → *Explore*. Read `chat.md` beside it.
- **Instance:** `explore` in `spry/spry.config.json`. Any value still `<…>` → stop and fill it with
  the developer first; never fall back to the development instance.
- **Asks:** area, depth and seed — take any already in `$ARGUMENTS`, ask the rest in one message.
- **Report only:** findings go to the reply and `.spry/explore/<seed>/`; a defect becomes a bug
  only when the person says yes.
